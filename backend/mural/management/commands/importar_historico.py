"""Importa o histórico do grupo a partir de listas em CSV (separadas por ";").

    python manage.py importar_historico lista.csv --conferir   # não grava no banco
    python manage.py importar_historico lista.csv              # grava

Colunas: ano;titulo;tipo;tier;indicado_por;data;ano_lancamento;tmdb_id
(data, ano_lancamento e tmdb_id são opcionais). Vários indicadores: Ana+Beto.

A conferência procura cada título no TMDB e pergunta, pelo número, qual é o certo nos
casos ambíguos. As escolhas ficam na coluna tmdb_id da própria lista. A importação só
grava se nenhuma linha tiver problema, e pode ser repetida: o que já entrou é pulado.
"""

import csv
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F

from mural import tmdb
from mural.models import Amigo, Filme, Sessao, Tier, Tipo
from mural.serializers import erros_da_sessao

OBRIGATORIAS = ["ano", "titulo", "tipo", "tier", "indicado_por"]
OPCIONAIS = ["data", "ano_lancamento", "tmdb_id"]
MAX_OPCOES = 8

# Entre títulos de mesmo nome, um é claramente o famoso quando tem muito mais votos.
VOTOS_MINIMOS = 100
VOTOS_VANTAGEM = 20


def normalizar(texto):
    """'X-Men '97' e 'x-men 97' viram o mesmo texto (sem acento, caixa ou pontuação)."""
    texto = unicodedata.normalize("NFKD", texto or "").casefold()
    return "".join(c for c in texto if c.isalnum())


def ler_numero(texto):
    """'2024' -> 2024; vazio -> None; qualquer outra coisa -> ValueError."""
    if not texto:
        return None
    if not (texto.isascii() and texto.isdigit()):
        raise ValueError(texto)
    return int(texto)


def ler_data(texto):
    """Aceita 2026-04-05 e 05/04/2026 (o Excel troca o formato ao salvar)."""
    if not texto:
        return None
    formato = "%d/%m/%Y" if "/" in texto else "%Y-%m-%d"
    return datetime.strptime(texto, formato).date()


class Lista:
    """Um arquivo CSV, que pode ser regravado com os tmdb_id escolhidos."""

    def __init__(self, caminho):
        self.caminho = caminho
        try:
            with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
                leitor = csv.DictReader(arquivo, delimiter=";")
                self.colunas = [(c or "").strip() for c in leitor.fieldnames or []]
                leitor.fieldnames = self.colunas
                registros = [(leitor.line_num, registro) for registro in leitor]
        except FileNotFoundError as erro:
            raise CommandError(f"Arquivo não encontrado: {caminho}") from erro
        except UnicodeDecodeError as erro:
            raise CommandError(
                f"{caminho}: salve o arquivo em UTF-8 (no Excel, \"CSV UTF-8\")."
            ) from erro

        faltam = [c for c in OBRIGATORIAS if c not in self.colunas]
        if faltam:
            raise CommandError(
                f"{caminho}: falta a coluna {', '.join(faltam)}. A primeira linha deve ser: "
                f"{';'.join(OBRIGATORIAS + OPCIONAIS)}"
            )
        self.linhas = [
            Linha(self, numero, registro)
            for numero, registro in registros
            if any(v.strip() for v in registro.values() if isinstance(v, str))
        ]

    def salvar(self):
        if "tmdb_id" not in self.colunas:
            self.colunas.append("tmdb_id")
        try:
            with open(self.caminho, "w", encoding="utf-8-sig", newline="") as arquivo:
                escritor = csv.writer(arquivo, delimiter=";")
                escritor.writerow(self.colunas)
                for linha in self.linhas:
                    valores = [linha.registro.get(c) or "" for c in self.colunas]
                    # Campos que sobraram numa linha com erro não podem se perder.
                    escritor.writerow(valores + (linha.registro.get(None) or []))
        except PermissionError as erro:
            raise CommandError(
                f"Não foi possível gravar {self.caminho}. Ele está aberto no Excel?"
            ) from erro


class Linha:
    """Uma linha da lista: um título exibido ao grupo."""

    def __init__(self, lista, numero, registro):
        self.lista, self.numero, self.registro = lista, numero, registro
        self.erros = []
        self.escolhido = None  # {"tmdb_id", "titulo", "ano_lancamento"}
        self.motivo = ""  # por que a escolha merece ser conferida (vazio = certa)
        self.opcoes = []  # candidatos, quando não dá para escolher sozinho

        # Colunas a mais (registro[None]) ou linha curta demais (valor None).
        if None in registro or None in registro.values():
            self.erros.append("A quantidade de campos não bate com o cabeçalho.")

        def campo(nome):
            return (registro.get(nome) or "").strip()

        self.titulo = campo("titulo")
        self.tipo = campo("tipo").lower().replace("é", "e")
        self.tier = campo("tier").upper() or None
        self.ano = self._ler(ler_numero, campo("ano"), "ano")
        self.data = self._ler(ler_data, campo("data"), "data")
        self.ano_lancamento = self._ler(
            ler_numero, campo("ano_lancamento"), "ano_lancamento"
        )
        self.tmdb_id = self._ler(ler_numero, campo("tmdb_id"), "tmdb_id")
        # Sem repetir ninguém, na ordem em que aparecem.
        apelidos = [p.strip() for p in campo("indicado_por").split("+") if p.strip()]
        self.apelidos = list({a.casefold(): a for a in apelidos}.values())
        if not self.erros:
            self._validar()

    def _ler(self, leitor, texto, nome):
        try:
            return leitor(texto)
        except ValueError:
            self.erros.append(f"{nome} inválido: {texto}")
            return None

    def _validar(self):
        if not self.titulo:
            self.erros.append("Falta o título.")
        if self.tipo not in Tipo.values:
            self.erros.append(f"tipo deve ser {' ou '.join(Tipo.values)}.")
        if self.tier and self.tier not in Tier.values:
            self.erros.append(f"tier deve ser uma destas: {', '.join(Tier.values)}.")
        if not self.apelidos:
            self.erros.append("Informe pelo menos um amigo que indicou o título.")
        for apelido in self.apelidos:
            if not 2 <= len(apelido) <= 50:
                self.erros.append(f"O apelido deve ter de 2 a 50 caracteres: {apelido}")
        if self.ano is None:
            self.erros.append("Falta o ano.")
        elif self.data and self.data.year != self.ano:
            self.erros.append("O ano deve ser o mesmo da data de exibição.")
        # As mesmas regras da API; o histórico é importado pela administradora.
        self.erros += erros_da_sessao(self.data, self.ano, self.tier, admin=True).values()

    def __str__(self):
        lancamento = f" ({self.ano_lancamento})" if self.ano_lancamento else ""
        return f"linha {self.numero}: {self.titulo}{lancamento}"

    def procurar(self):
        """Acha o título no TMDB: preenche `escolhido`, `opcoes` ou `erros`."""
        try:
            if self.tmdb_id:
                filme = Filme.objects.filter(tipo=self.tipo, tmdb_id=self.tmdb_id).first()
                if filme:
                    dados = {"titulo": filme.titulo, "ano_lancamento": filme.ano_lancamento}
                else:
                    dados = tmdb.detalhes(self.tmdb_id, self.tipo)
                self.escolhido = {**dados, "tmdb_id": self.tmdb_id}
                return
            achados = tmdb.candidatos(self.titulo, self.tipo, self.ano_lancamento)
            outro_ano = False
            if not achados and self.ano_lancamento:
                achados = tmdb.candidatos(self.titulo, self.tipo)
                outro_ano = True
        except tmdb.TMDBChaveError as erro:
            raise CommandError(
                f"{erro} Confira a TMDB_API_KEY: a chave da API tem 32 caracteres, "
                "e o token de leitura começa com eyJ."
            ) from erro
        except tmdb.TMDBError as erro:
            self.erros.append(str(erro))
            return
        if not achados:
            self.erros.append(
                "Nada encontrado no TMDB. Confira o nome ou preencha o tmdb_id."
            )
            return
        self._escolher(achados, outro_ano)

    def _escolher(self, achados, outro_ano):
        nome = normalizar(self.titulo)
        iguais = [
            c
            for c in achados
            if nome and nome in (normalizar(c["titulo"]), normalizar(c["titulo_original"]))
        ]
        if len(iguais) > 1 and self.ano_lancamento:
            # O filtro do TMDB também aceita o ano de relançamentos.
            do_ano = [c for c in iguais if c["ano_lancamento"] == self.ano_lancamento]
            iguais = do_ano or iguais

        unico, motivo = None, ""
        if len(iguais) == 1:
            unico = iguais[0]
        elif len(iguais) > 1:
            primeiro, segundo = sorted(iguais, key=lambda c: -c["votos"])[:2]
            if primeiro["votos"] >= max(VOTOS_MINIMOS, VOTOS_VANTAGEM * segundo["votos"]):
                unico, motivo = primeiro, "há outros com o mesmo nome, bem menos conhecidos"
        elif len(achados) == 1:
            unico, motivo = achados[0], "nome diferente, único resultado"

        # Ano informado não bate: só aceita sozinho a diferença de 1 (estreia em festival).
        if unico and self.ano_lancamento and unico["ano_lancamento"] != self.ano_lancamento:
            distancia = abs((unico["ano_lancamento"] or 0) - self.ano_lancamento)
            if distancia > 1 or (outro_ano and motivo):
                unico = None
            else:
                motivo = motivo or "ano diferente do informado"

        if unico:
            self.escolhido, self.motivo = unico, motivo
        else:
            outros = [c for c in achados if c not in iguais]
            self.opcoes = (iguais + outros)[:MAX_OPCOES]

    def definir_tmdb_id(self, tmdb_id):
        """Guarda na lista o título escolhido à mão."""
        self.opcoes, self.motivo, self.tmdb_id = [], "", tmdb_id
        self.registro["tmdb_id"] = str(tmdb_id)
        self.lista.salvar()


def descrever(item, tipo):
    ano = item.get("ano_lancamento") or "sem ano"
    original = item.get("titulo_original")
    extra = f" [{original}]" if original and original != item["titulo"] else ""
    caminho = "tv" if tipo == Tipo.SERIE else "movie"
    return (
        f"{item['titulo']} ({ano}){extra} "
        f"https://www.themoviedb.org/{caminho}/{item['tmdb_id']}"
    )


class Command(BaseCommand):
    help = "Importa o histórico do grupo (títulos, sessões, tiers e indicadores) de arquivos CSV."

    def add_arguments(self, parser):
        parser.add_argument("arquivos", nargs="+", help="um ou mais arquivos .csv")
        parser.add_argument(
            "--conferir",
            action="store_true",
            help="não grava no banco: confere as linhas, procura no TMDB e pergunta os ambíguos",
        )
        parser.add_argument(
            "--sem-perguntas",
            action="store_true",
            help="com --conferir, só lista os casos ambíguos",
        )

    def handle(self, *args, arquivos, conferir, sem_perguntas, **options):
        # Títulos originais (em coreano, por exemplo) não podem derrubar o terminal.
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(errors="replace")

        linhas = [linha for caminho in arquivos for linha in Lista(caminho).linhas]
        if not linhas:
            raise CommandError("A lista está vazia.")
        if not settings.TMDB_API_KEY:
            raise CommandError("Defina a variável de ambiente TMDB_API_KEY antes de importar.")
        self.varios = len(arquivos) > 1

        self._conferir_datas_repetidas(linhas)
        self.stdout.write(f"Procurando {len(linhas)} títulos no TMDB...")
        for linha in linhas:
            if not linha.erros:
                linha.procurar()

        ambiguas = [linha for linha in linhas if linha.opcoes]
        if conferir and not sem_perguntas and ambiguas and self._pode_perguntar():
            self._perguntar(ambiguas)
        self._conferir_datas_ocupadas(linhas)
        self._relatorio(linhas, completo=conferir)

        pendentes = [linha for linha in linhas if linha.erros or linha.opcoes]
        if conferir:
            if not pendentes:
                self.stdout.write(
                    self.style.SUCCESS("Tudo certo. Rode sem --conferir para gravar.")
                )
            return
        if pendentes:
            raise CommandError(
                f"{len(pendentes)} linha(s) com pendência: nada foi gravado. "
                "Rode com --conferir para resolver."
            )
        self._importar(linhas)

    # ---------------------------------------------------------- conferência

    def _conferir_datas_repetidas(self, linhas):
        vezes = Counter(linha.data for linha in linhas if linha.data)
        for linha in linhas:
            if vezes[linha.data] > 1:
                linha.erros.append(f"Há mais de um título em {linha.data:%d/%m/%Y}.")

    def _conferir_datas_ocupadas(self, linhas):
        """Data que já tem sessão de outro título no banco."""
        for linha in linhas:
            if not (linha.data and linha.escolhido):
                continue
            sessao = Sessao.objects.filter(data_exibicao=linha.data).first()
            if sessao and not self._mesmo_titulo(sessao.filme, linha):
                linha.erros.append(
                    f"Já existe no site uma sessão em {linha.data:%d/%m/%Y}: "
                    f"{sessao.filme.titulo}."
                )

    def _mesmo_titulo(self, filme, linha):
        return (filme.tipo, filme.tmdb_id) == (linha.tipo, linha.escolhido["tmdb_id"])

    def _pode_perguntar(self):
        return sys.stdin is not None and sys.stdin.isatty()

    def _perguntar(self, ambiguas):
        self.stdout.write(
            f"\n{len(ambiguas)} título(s) para escolher. Digite o número da opção, "
            "\"id 123\" para informar outro tmdb_id, Enter para pular ou \"s\" para sair.\n"
        )
        for linha in ambiguas:
            self._listar_opcoes(linha)
            while True:
                resposta = self._perguntar_opcao()
                if resposta == "s":
                    return
                if not resposta:
                    break
                tmdb_id = self._interpretar(resposta, linha.opcoes)
                if tmdb_id is None:
                    self.stdout.write("Opção inválida.")
                    continue
                opcao = next((o for o in linha.opcoes if o["tmdb_id"] == tmdb_id), None)
                if opcao is None:
                    try:
                        opcao = {**tmdb.detalhes(tmdb_id, linha.tipo), "tmdb_id": tmdb_id}
                    except tmdb.TMDBError as erro:
                        self.stdout.write(str(erro))
                        continue
                    self.stdout.write(f"Escolhido: {descrever(opcao, linha.tipo)}")
                linha.escolhido = opcao
                linha.definir_tmdb_id(tmdb_id)
                break

    def _perguntar_opcao(self):
        try:
            return input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "s"

    def _interpretar(self, resposta, opcoes):
        livre = re.fullmatch(r"id\s*(\d{1,9})", resposta, re.ASCII)
        if livre:
            return int(livre[1])
        if resposta.isascii() and resposta.isdigit() and 1 <= int(resposta) <= len(opcoes):
            return opcoes[int(resposta) - 1]["tmdb_id"]
        return None

    def _nome(self, linha):
        return f"{linha.lista.caminho}, {linha}" if self.varios else str(linha)

    def _listar_opcoes(self, linha):
        self.stdout.write(f"\n{self._nome(linha)} - {linha.tipo}")
        for numero, opcao in enumerate(linha.opcoes, start=1):
            self.stdout.write(f"  {numero}) {descrever(opcao, linha.tipo)}")

    def _relatorio(self, linhas, completo):
        com_erro = [linha for linha in linhas if linha.erros]
        ambiguas = [linha for linha in linhas if linha.opcoes and not linha.erros]
        achadas = [linha for linha in linhas if linha.escolhido and not linha.erros]

        if completo:
            certas = [linha for linha in achadas if not linha.motivo]
            self._titulo(f"Encontrados ({len(certas)})", certas)
            for linha in certas:
                self._mostrar_escolha(linha)
        duvidosas = [linha for linha in achadas if linha.motivo]
        self._titulo(f"Encontrados, mas confira ({len(duvidosas)})", duvidosas)
        for linha in duvidosas:
            self._mostrar_escolha(linha)
        if duvidosas:
            self.stdout.write("  (se algum estiver errado, preencha o tmdb_id na lista)")

        self._titulo(f"Falta escolher ({len(ambiguas)})", ambiguas)
        for linha in ambiguas:
            self._listar_opcoes(linha)

        self._titulo(f"Com problema ({len(com_erro)})", com_erro)
        for linha in com_erro:
            self.stdout.write(f"  {self._nome(linha)}: {' '.join(linha.erros)}")

        repetidas = Counter(
            (linha.ano, linha.tipo, linha.escolhido["tmdb_id"]) for linha in achadas
        )
        vezes = [
            linha
            for linha in achadas
            if repetidas[linha.ano, linha.tipo, linha.escolhido["tmdb_id"]] > 1
        ]
        self._titulo("Mais de uma vez no mesmo ano (o grupo reviu?)", vezes)
        for linha in vezes:
            self.stdout.write(f"  {self._nome(linha)}")

        conhecidos = {a.casefold() for a in Amigo.objects.values_list("apelido", flat=True)}
        novos = {
            apelido.casefold(): apelido
            for linha in linhas
            for apelido in linha.apelidos
            if apelido.casefold() not in conhecidos
        }
        if novos:
            self.stdout.write(f"\nAmigos novos: {', '.join(sorted(novos.values()))}")
        self.stdout.write("")

    def _titulo(self, texto, itens):
        if itens:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n{texto}"))

    def _mostrar_escolha(self, linha):
        motivo = f" ({linha.motivo})" if linha.motivo else ""
        self.stdout.write(
            f"  {self._nome(linha)} -> {descrever(linha.escolhido, linha.tipo)}{motivo}"
        )

    # ----------------------------------------------------------- importação

    @transaction.atomic
    def _importar(self, linhas):
        """Grava tudo ou nada."""
        amigos = {a.apelido.casefold(): a for a in Amigo.objects.all()}
        # Sessões que já estavam no site, para que repetir a importação não duplique nada.
        # As com data são reconhecidas primeiro, para não serem confundidas com as sem data.
        usadas = set()
        novas = puladas = 0

        for linha in sorted(linhas, key=lambda linha: linha.data is None):
            try:
                filme = tmdb.obter_ou_criar_filme(linha.escolhido["tmdb_id"], linha.tipo)
            except tmdb.TMDBError as erro:
                raise CommandError(
                    f"{self._nome(linha)}: {erro} Nada foi gravado."
                ) from erro

            existentes = Sessao.objects.filter(filme=filme).exclude(pk__in=usadas)
            if linha.data:
                existentes = existentes.filter(data_exibicao=linha.data)
            else:
                # A data pode ter sido preenchida no site depois da importação.
                existentes = existentes.filter(ano=linha.ano).order_by(
                    F("data_exibicao").asc(nulls_first=True)
                )
            sessao = existentes.first()
            if sessao:
                usadas.add(sessao.pk)
                puladas += 1
                continue

            sessao = Sessao.objects.create(
                filme=filme, ano=linha.ano, data_exibicao=linha.data, tier=linha.tier
            )
            for apelido in linha.apelidos:
                chave = apelido.casefold()
                if chave not in amigos:
                    amigos[chave] = Amigo.objects.create(apelido=apelido)
                sessao.sugerido_por.add(amigos[chave])
            usadas.add(sessao.pk)
            novas += 1

        resumo = f"{novas} sessão(ões) importada(s)."
        if puladas:
            resumo += f" {puladas} já estava(m) no site e foi(ram) pulada(s)."
        self.stdout.write(self.style.SUCCESS(resumo))
