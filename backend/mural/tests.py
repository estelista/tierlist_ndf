import io
import os
import shutil
import tempfile
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase

from . import tmdb
from .models import Amigo, Comentario, Filme, FotoComentario, Sessao

User = get_user_model()
SENHA = "Tela-cheia-2026"
MEDIA_TESTE = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(MEDIA_TESTE, ignore_errors=True)


def imagem_png(nome="foto.png", cor=(200, 50, 50)):
    """Gera uma imagem PNG válida em memória, pronta para enviar num formulário."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), cor).save(buffer, format="PNG")
    return SimpleUploadedFile(nome, buffer.getvalue(), content_type="image/png")


class BaseTestCase(APITestCase):
    def setUp(self):
        cache.clear()  # zera os contadores de throttling entre os testes
        self.hoje = timezone.localdate()
        self.admin = User.objects.create_user("dona", password=SENHA, is_staff=True)
        self.ana = self.novo_amigo("Ana", "/icones/ana.png")
        self.beto = self.novo_amigo("Beto")
        self.f1 = Filme.objects.create(titulo="Pulp Fiction", ano_lancamento=1994, diretor="Quentin Tarantino", genero="Crime")
        self.f2 = Filme.objects.create(titulo="Parasita", ano_lancamento=2019, diretor="Bong Joon-ho", genero="Suspense")
        self.f3 = Filme.objects.create(titulo="Cats", ano_lancamento=2019, diretor="Tom Hooper", genero="Musical")

    def novo_amigo(self, apelido, icone=""):
        user = User.objects.create_user(apelido.lower(), password=SENHA)
        return Amigo.objects.create(apelido=apelido, icone_url=icone, user=user)

    def entrar(self, quem):
        """Autentica as próximas requisições como um Amigo ou um User."""
        user = quem.user if isinstance(quem, Amigo) else quem
        self.client.force_authenticate(user=user)

    def sair(self):
        self.client.force_authenticate(user=None)

    def criar_sessao(self, filme, amigos, data, tier=None, criado_por=None):
        """Cria uma sessão com um ou mais amigos indicando. 'data' é um date."""
        sessao = Sessao.objects.create(
            filme=filme, data_exibicao=data, tier=tier, criado_por=criado_por
        )
        sessao.sugerido_por.set(amigos)
        return sessao

    def nova_sessao(self, filme, amigo, dias_atras, tier=None):
        return self.criar_sessao(filme, [amigo], self.hoje - timedelta(days=dias_atras), tier)

    def sessao_so_com_ano(self, filme, amigos, ano, tier):
        """Sessão do histórico (anos 1 e 2): só o ano é conhecido."""
        sessao = Sessao.objects.create(filme=filme, ano=ano, tier=tier)
        sessao.sugerido_por.set(amigos)
        return sessao


# ------------------------------------------------------------ sessões (CRUD)


class CrudSessaoTests(BaseTestCase):
    def test_crud_completo(self):
        self.entrar(self.ana)
        data = self.hoje - timedelta(days=7)
        payload = {
            "filme": self.f1.id,
            "sugerido_por": [self.ana.id],
            "data_exibicao": str(data),
            "tier": "A",
        }
        r = self.client.post("/api/sessoes/", payload, format="json")
        self.assertEqual(r.status_code, 201)
        pk = r.data["id"]
        self.assertEqual(r.data["filme_titulo"], "Pulp Fiction")
        self.assertEqual(r.data["ano"], data.year)  # o ano sai da data
        self.assertTrue(r.data["pode_editar"])
        self.assertEqual(Sessao.objects.get(pk=pk).criado_por, self.ana.user)

        self.sair()  # o mural é público
        self.assertEqual(self.client.get("/api/sessoes/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/sessoes/{pk}/").status_code, 200)

        self.entrar(self.ana)
        payload["tier"] = "S"
        r = self.client.put(f"/api/sessoes/{pk}/", payload, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tier"], "S")

        self.assertEqual(self.client.delete(f"/api/sessoes/{pk}/").status_code, 204)
        self.assertEqual(self.client.get(f"/api/sessoes/{pk}/").status_code, 404)

    def test_visitante_nao_cria_sessao(self):
        r = self.client.post(
            "/api/sessoes/",
            {"filme": self.f1.id, "sugerido_por": [self.ana.id],
             "data_exibicao": str(self.hoje - timedelta(days=1)), "tier": "A"},
            format="json",
        )
        self.assertEqual(r.status_code, 401)

    def test_so_o_dono_ou_a_admin_altera_a_sessao(self):
        s = self.criar_sessao(self.f1, [self.ana], self.hoje - timedelta(days=5), "A", criado_por=self.ana.user)
        url = f"/api/sessoes/{s.id}/"

        self.entrar(self.beto)
        self.assertEqual(self.client.patch(url, {"tier": "B"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertFalse(self.client.get(url).data["pode_editar"])

        self.entrar(self.ana)
        self.assertEqual(self.client.patch(url, {"tier": "B"}, format="json").status_code, 200)

        self.entrar(self.admin)
        r = self.client.patch(url, {"tier": "C"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tier"], "C")

    def test_sessao_com_mais_de_um_amigo_e_icones(self):
        self.entrar(self.ana)
        r = self.client.post(
            "/api/sessoes/",
            {"filme": self.f2.id, "sugerido_por": [self.ana.id, self.beto.id],
             "data_exibicao": str(self.hoje - timedelta(days=2)), "tier": "A"},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        detalhe = r.data["sugerido_por_detalhe"]
        self.assertEqual(sorted(a["apelido"] for a in detalhe), ["Ana", "Beto"])
        icones = {a["apelido"]: a["icone_url"] for a in detalhe}
        self.assertEqual(icones["Ana"], "/icones/ana.png")

    def test_exige_pelo_menos_um_amigo(self):
        self.entrar(self.ana)
        r = self.client.post(
            "/api/sessoes/",
            {"filme": self.f1.id, "sugerido_por": [],
             "data_exibicao": str(self.hoje - timedelta(days=1)), "tier": "A"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("sugerido_por", r.data)

    def test_o_mesmo_filme_pode_ter_varias_sessoes(self):
        self.entrar(self.ana)
        for dias in (30, 10):
            r = self.client.post(
                "/api/sessoes/",
                {"filme": self.f1.id, "sugerido_por": [self.ana.id],
                 "data_exibicao": str(self.hoje - timedelta(days=dias)), "tier": "A"},
                format="json",
            )
            self.assertEqual(r.status_code, 201)
        self.assertEqual(self.f1.sessoes.count(), 2)

    def test_filme_com_sessoes_nao_pode_ser_apagado(self):
        self.nova_sessao(self.f1, self.ana, 3, "A")
        self.entrar(self.admin)
        r = self.client.delete(f"/api/filmes/{self.f1.id}/")
        self.assertEqual(r.status_code, 400)
        self.assertTrue(Filme.objects.filter(pk=self.f1.id).exists())


# ------------------------------------------------------------- validações


class ValidacaoTests(BaseTestCase):
    def test_tier_invalida_retorna_400(self):
        self.entrar(self.ana)
        r = self.client.post(
            "/api/sessoes/",
            {"filme": self.f1.id, "sugerido_por": [self.ana.id],
             "data_exibicao": str(self.hoje - timedelta(days=1)), "tier": "Z"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("tier", r.data)

    def test_data_duplicada_retorna_400(self):
        self.nova_sessao(self.f1, self.ana, 5, "A")
        self.entrar(self.ana)
        r = self.client.post(
            "/api/sessoes/",
            {"filme": self.f2.id, "sugerido_por": [self.beto.id],
             "data_exibicao": str(self.hoje - timedelta(days=5)), "tier": "B"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("data_exibicao", r.data)

    def test_ano_de_lancamento_invalido(self):
        self.entrar(self.admin)
        r = self.client.post(
            "/api/filmes/", {"titulo": "Filme X", "ano_lancamento": 1800}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("ano_lancamento", r.data)

    def test_amigo_comum_nao_cadastra_filme_diretamente(self):
        self.entrar(self.ana)
        r = self.client.post(
            "/api/filmes/", {"titulo": "Filme X", "ano_lancamento": 2000}, format="json"
        )
        self.assertEqual(r.status_code, 403)

    def test_sessao_precisa_de_filme_ou_tmdb_id(self):
        self.entrar(self.ana)
        r = self.client.post(
            "/api/sessoes/",
            {"sugerido_por": [self.ana.id],
             "data_exibicao": str(self.hoje - timedelta(days=1)), "tier": "A"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("filme", r.data)


# ---------------------------------------------------- regras de negócio


class RegraDeNegocioTests(BaseTestCase):
    def test_nao_atribui_tier_a_sessao_futura(self):
        self.entrar(self.ana)
        r = self.client.post(
            "/api/sessoes/",
            {"filme": self.f1.id, "sugerido_por": [self.ana.id],
             "data_exibicao": str(self.hoje + timedelta(days=3)), "tier": "S"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("tier", r.data)

    def test_sessao_futura_sem_tier_e_permitida(self):
        self.entrar(self.ana)
        r = self.client.post(
            "/api/sessoes/",
            {"filme": self.f1.id, "sugerido_por": [self.ana.id],
             "data_exibicao": str(self.hoje + timedelta(days=3))},
            format="json",
        )
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.data["tier"])

    def test_sessao_que_ja_aconteceu_exige_tier(self):
        self.entrar(self.ana)
        r = self.client.post(
            "/api/sessoes/",
            {"filme": self.f1.id, "sugerido_por": [self.ana.id],
             "data_exibicao": str(self.hoje - timedelta(days=3))},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("tier", r.data)

    def test_sessao_de_hoje_exige_tier(self):
        self.entrar(self.ana)
        r = self.client.post(
            "/api/sessoes/",
            {"filme": self.f1.id, "sugerido_por": [self.ana.id],
             "data_exibicao": str(self.hoje)},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("tier", r.data)

    def test_patch_de_tier_em_sessao_futura_e_barrado(self):
        s = self.criar_sessao(self.f1, [self.ana], self.hoje + timedelta(days=2))
        self.entrar(self.admin)
        r = self.client.patch(f"/api/sessoes/{s.id}/", {"tier": "B"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_agendamento_vira_sessao_avaliada_ao_receber_tier(self):
        # Sessão que já aconteceu e foi cadastrada antes (sem tier): ao editar, exige tier.
        s = self.criar_sessao(self.f1, [self.ana], self.hoje, criado_por=self.ana.user)
        self.entrar(self.ana)
        url = f"/api/sessoes/{s.id}/"
        self.assertEqual(self.client.patch(url, {"sugerido_por": [self.ana.id]}, format="json").status_code, 400)
        r = self.client.patch(url, {"tier": "A"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tier"], "A")

    def test_nao_comenta_sessao_futura(self):
        s = self.criar_sessao(self.f1, [self.ana], self.hoje + timedelta(days=2))
        self.entrar(self.beto)
        r = self.client.post(
            "/api/comentarios/", {"sessao": s.id, "texto": "Mal posso esperar"}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("sessao", r.data)

    def test_comenta_sessao_passada(self):
        s = self.nova_sessao(self.f1, self.ana, 3, "A")
        self.entrar(self.beto)
        r = self.client.post(
            "/api/comentarios/", {"sessao": s.id, "texto": "Ótimo filme!"}, format="json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Comentario.objects.count(), 1)


class AnoEDataTests(BaseTestCase):
    def payload(self, **extra):
        base = {"filme": self.f1.id, "sugerido_por": [self.ana.id], "tier": "S"}
        base.update(extra)
        return base

    def test_amigo_precisa_informar_a_data_exata(self):
        self.entrar(self.ana)
        r = self.client.post("/api/sessoes/", self.payload(ano=2024), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("data_exibicao", r.data)

    def test_admin_cadastra_sessao_so_com_o_ano(self):
        self.entrar(self.admin)
        r = self.client.post("/api/sessoes/", self.payload(ano=2024), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["ano"], 2024)
        self.assertIsNone(r.data["data_exibicao"])
        self.assertEqual(r.data["ano_do_grupo"], 1)

    def test_varias_sessoes_sem_data_no_mesmo_ano(self):
        self.entrar(self.admin)
        for filme in (self.f1, self.f2):
            r = self.client.post(
                "/api/sessoes/", self.payload(filme=filme.id, ano=2024), format="json"
            )
            self.assertEqual(r.status_code, 201)

    def test_ano_atual_exige_data_exata(self):
        self.entrar(self.admin)
        r = self.client.post("/api/sessoes/", self.payload(ano=self.hoje.year), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("ano", r.data)

    def test_ano_anterior_ao_inicio_do_grupo(self):
        self.entrar(self.admin)
        r = self.client.post("/api/sessoes/", self.payload(ano=2023), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("ano", r.data)

    def test_ano_precisa_bater_com_a_data(self):
        self.entrar(self.admin)
        data = self.hoje - timedelta(days=5)
        r = self.client.post(
            "/api/sessoes/",
            self.payload(data_exibicao=str(data), ano=data.year - 1),
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("ano", r.data)


# --------------------------------------------------------------- consultas


class ConsultaTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.s_a = self.nova_sessao(self.f1, self.ana, 30, "S")
        self.s_b = self.nova_sessao(self.f2, self.beto, 20, "VTNC")
        # indicação em conjunto: Ana e Beto
        self.s_c = self.criar_sessao(self.f3, [self.ana, self.beto], self.hoje - timedelta(days=10), "B")

    def titulos(self, url):
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        return [i["filme_titulo"] for i in r.data["results"]]

    def test_filtro_por_tier(self):
        self.assertEqual(self.titulos("/api/sessoes/?tier=S"), ["Pulp Fiction"])

    def test_filtro_por_sugestor_inclui_indicacoes_em_conjunto(self):
        self.assertEqual(
            sorted(self.titulos("/api/sessoes/?sugerido_por=ana")), ["Cats", "Pulp Fiction"]
        )
        self.assertEqual(
            sorted(self.titulos("/api/sessoes/?sugerido_por=beto")), ["Cats", "Parasita"]
        )

    def test_filtro_por_ano_e_por_filme(self):
        self.sessao_so_com_ano(self.f1, [self.ana], 2024, "C")
        self.assertEqual(self.titulos("/api/sessoes/?ano=2024"), ["Pulp Fiction"])
        exibicoes = self.titulos(f"/api/sessoes/?filme={self.f1.id}")
        self.assertEqual(exibicoes, ["Pulp Fiction", "Pulp Fiction"])

    def test_busca_textual(self):
        self.assertEqual(self.titulos("/api/sessoes/?search=tarantino"), ["Pulp Fiction"])
        # Beto indicou 2 filmes, e um deles em conjunto: sem duplicar resultados
        self.assertEqual(sorted(self.titulos("/api/sessoes/?search=beto")), ["Cats", "Parasita"])

    def test_ordenacao_por_tier_respeita_o_ranking(self):
        # S > B > VTNC (e não ordem alfabética)
        self.assertEqual(
            self.titulos("/api/sessoes/?ordering=-tier_rank"),
            ["Pulp Fiction", "Cats", "Parasita"],
        )

    def test_ordenacao_padrao_e_mais_recente_primeiro(self):
        self.assertEqual(self.titulos("/api/sessoes/"), ["Cats", "Parasita", "Pulp Fiction"])

    def test_paginacao(self):
        r = self.client.get("/api/sessoes/?page_size=2")
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data["results"]), 2)
        self.assertIsNotNone(r.data["next"])


# -------------------------------------------- mural: tier lists, anos, próximas


class TierListsTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.criar_sessao(self.f1, [self.ana], date(2024, 3, 1), "S")
        self.criar_sessao(self.f2, [self.beto], date(2025, 5, 1), "A")
        self.criar_sessao(self.f3, [self.ana, self.beto], date(2025, 6, 1), "VTNC")
        # histórico sem data exata (só o ano)
        self.sessao_so_com_ano(self.f1, [self.ana], 2024, "C")
        # agendada/sem tier: não aparece na tier list
        self.criar_sessao(self.f3, [self.ana], date(2025, 7, 1))

    def test_agrupa_por_ano_e_tier(self):
        r = self.client.get("/api/sessoes/tier-lists/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([a["ano"] for a in r.data], [2025, 2024])
        self.assertEqual(list(r.data[0]["tiers"].keys()), ["S", "A", "B", "C", "VTNC"])
        self.assertEqual(len(r.data[0]["tiers"]["A"]), 1)
        self.assertEqual(len(r.data[0]["tiers"]["VTNC"]), 1)
        self.assertEqual(sum(len(v) for v in r.data[0]["tiers"].values()), 2)

    def test_sessoes_sem_data_entram_no_ano_delas(self):
        r = self.client.get("/api/sessoes/tier-lists/?ano=2024")
        tiers = r.data[0]["tiers"]
        self.assertEqual(len(tiers["S"]), 1)
        self.assertEqual(len(tiers["C"]), 1)
        self.assertIsNone(tiers["C"][0]["data_exibicao"])

    def test_nomeia_os_anos_do_grupo(self):
        r = self.client.get("/api/sessoes/tier-lists/")
        nomes = {a["ano"]: a["nome"] for a in r.data}
        self.assertEqual(nomes, {2024: "Ano 1", 2025: "Ano 2"})

    def test_filtro_por_ano(self):
        r = self.client.get("/api/sessoes/tier-lists/?ano=2024")
        self.assertEqual([a["ano"] for a in r.data], [2024])

    def test_ano_sem_filmes_vem_com_tiers_vazias(self):
        r = self.client.get("/api/sessoes/tier-lists/?ano=2030")
        self.assertEqual([a["ano"] for a in r.data], [2030])
        self.assertEqual(r.data[0]["nome"], "Ano 7")
        self.assertEqual(sum(len(v) for v in r.data[0]["tiers"].values()), 0)

    def test_filmes_da_tier_list_trazem_icones_dos_amigos(self):
        r = self.client.get("/api/sessoes/tier-lists/?ano=2025")
        vtnc = r.data[0]["tiers"]["VTNC"][0]
        self.assertEqual(
            sorted(a["apelido"] for a in vtnc["sugerido_por_detalhe"]), ["Ana", "Beto"]
        )


class AnosTests(BaseTestCase):
    def test_lista_os_anos_do_inicio_do_grupo_ate_o_atual(self):
        self.criar_sessao(self.f1, [self.ana], date(2024, 3, 1), "S")
        r = self.client.get("/api/sessoes/anos/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["ano_atual"], self.hoje.year)
        anos = r.data["anos"]
        self.assertEqual(anos[0], {"ano": 2024, "ano_do_grupo": 1, "nome": "Ano 1", "total": 1})
        self.assertEqual(anos[-1]["ano"], self.hoje.year)
        self.assertEqual(len(anos), self.hoje.year - 2024 + 1)

    def test_ano_atual_aparece_mesmo_sem_filmes(self):
        r = self.client.get("/api/sessoes/anos/")
        self.assertEqual(r.data["anos"][-1], {
            "ano": self.hoje.year,
            "ano_do_grupo": self.hoje.year - 2024 + 1,
            "nome": f"Ano {self.hoje.year - 2024 + 1}",
            "total": 0,
        })


class ProximasTests(BaseTestCase):
    def test_lista_so_as_futuras_sem_tier_em_ordem_de_data(self):
        longe = self.criar_sessao(self.f2, [self.beto], self.hoje + timedelta(days=9))
        perto = self.criar_sessao(self.f1, [self.ana], self.hoje + timedelta(days=2))
        self.nova_sessao(self.f3, self.ana, 4, "A")  # passada: fora
        r = self.client.get("/api/sessoes/proximas/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([s["id"] for s in r.data], [perto.id, longe.id])

    def test_sessao_de_hoje_sem_tier_aparece_ate_ser_avaliada(self):
        s = self.criar_sessao(self.f1, [self.ana], self.hoje)
        self.assertEqual([x["id"] for x in self.client.get("/api/sessoes/proximas/").data], [s.id])
        s.tier = "A"
        s.save()
        self.assertEqual(self.client.get("/api/sessoes/proximas/").data, [])


# ---------------------------------------------------------------- contas


@override_settings(CODIGO_CONVITE="convite-teste")
class ContasTests(BaseTestCase):
    def registrar(self, apelido="Carla", **extra):
        corpo = {"apelido": apelido, "senha": SENHA, "codigo_convite": "convite-teste"}
        corpo.update(extra)
        return self.client.post("/api/auth/registro/", corpo, format="json")

    def login(self, usuario, senha=SENHA):
        return self.client.post(
            "/api/auth/login/", {"username": usuario, "password": senha}, format="json"
        )

    def test_cadastro_cria_conta_pendente(self):
        r = self.registrar()
        self.assertEqual(r.status_code, 201)
        carla = User.objects.get(username="Carla")
        self.assertFalse(carla.is_active)
        self.assertTrue(carla.check_password(SENHA))

    def test_codigo_de_convite_errado_e_recusado(self):
        r = self.registrar(codigo_convite="chute")
        self.assertEqual(r.status_code, 400)
        self.assertIn("codigo_convite", r.data)
        self.assertFalse(User.objects.filter(username="Carla").exists())

    @override_settings(CODIGO_CONVITE="")
    def test_cadastro_desligado_sem_codigo_configurado(self):
        self.assertEqual(self.registrar(codigo_convite="").status_code, 400)

    def test_apelido_repetido_e_recusado_sem_diferenciar_maiusculas(self):
        r = self.registrar(apelido="ANA")
        self.assertEqual(r.status_code, 400)
        self.assertIn("apelido", r.data)

    def test_senha_fraca_e_recusada(self):
        r = self.registrar(senha="123")
        self.assertEqual(r.status_code, 400)
        self.assertIn("senha", r.data)

    def test_conta_pendente_nao_entra_e_recebe_aviso_claro(self):
        self.registrar()
        r = self.login("Carla")
        self.assertEqual(r.status_code, 401)
        self.assertIn("aprovação", r.data["detail"])

    def test_senha_errada_recebe_mensagem_generica(self):
        r = self.login("ana", "errada")
        self.assertEqual(r.status_code, 401)
        self.assertIn("incorretos", r.data["detail"])

    def test_login_devolve_tokens_e_dados_e_ignora_maiusculas(self):
        r = self.login("ANA")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)
        self.assertEqual(r.data["usuario"]["apelido"], "Ana")
        self.assertEqual(r.data["usuario"]["icone_url"], "/icones/ana.png")
        self.assertFalse(r.data["usuario"]["is_admin"])

    def test_token_funciona_na_api(self):
        token = self.login("ana").data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        r = self.client.get("/api/auth/eu/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["apelido"], "Ana")

    def test_eu_exige_login(self):
        self.assertEqual(self.client.get("/api/auth/eu/").status_code, 401)

    def test_so_a_admin_ve_os_pedidos_de_cadastro(self):
        self.registrar()
        self.assertEqual(self.client.get("/api/cadastros/").status_code, 401)
        self.entrar(self.ana)
        self.assertEqual(self.client.get("/api/cadastros/").status_code, 403)
        self.entrar(self.admin)
        r = self.client.get("/api/cadastros/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([c["apelido"] for c in r.data], ["Carla"])
        self.assertFalse(r.data[0]["amigo_existente"])

    def test_aprovar_cria_o_amigo_e_libera_o_login(self):
        self.registrar()
        carla = User.objects.get(username="Carla")
        self.entrar(self.ana)
        self.assertEqual(self.client.post(f"/api/cadastros/{carla.id}/aprovar/").status_code, 403)

        self.entrar(self.admin)
        r = self.client.post(
            f"/api/cadastros/{carla.id}/aprovar/", {"icone_url": "/icones/carla.png"}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["apelido"], "Carla")
        carla.refresh_from_db()
        self.assertTrue(carla.is_active)
        self.assertEqual(carla.amigo.icone_url, "/icones/carla.png")

        self.sair()
        self.assertEqual(self.login("carla").status_code, 200)
        self.entrar(self.admin)
        self.assertEqual(self.client.get("/api/cadastros/").data, [])

    def test_aprovar_liga_a_conta_ao_amigo_do_historico(self):
        caio = Amigo.objects.create(apelido="Caio", icone_url="/icones/caio.png")
        self.registrar(apelido="caio")
        pendente = User.objects.get(username="caio")
        self.entrar(self.admin)
        self.assertTrue(self.client.get("/api/cadastros/").data[0]["amigo_existente"])

        r = self.client.post(f"/api/cadastros/{pendente.id}/aprovar/")
        self.assertEqual(r.status_code, 200)
        caio.refresh_from_db()
        self.assertEqual(caio.user, pendente)
        self.assertEqual(caio.icone_url, "/icones/caio.png")  # mantém o ícone
        self.assertEqual(Amigo.objects.filter(apelido__iexact="caio").count(), 1)

    def test_recusar_apaga_o_pedido(self):
        self.registrar()
        carla = User.objects.get(username="Carla")
        self.entrar(self.admin)
        self.assertEqual(self.client.post(f"/api/cadastros/{carla.id}/recusar/").status_code, 204)
        self.assertFalse(User.objects.filter(username="Carla").exists())

    def test_cadastro_tem_limite_de_tentativas(self):
        for _ in range(5):
            self.assertEqual(self.registrar(codigo_convite="chute").status_code, 400)
        self.assertEqual(self.registrar(codigo_convite="chute").status_code, 429)


# ----------------------------------------------------- comentários e fotos


@override_settings(MEDIA_ROOT=MEDIA_TESTE)
class ComentarioTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.sessao = self.nova_sessao(self.f1, self.ana, 3, "A")

    def comentar(self, **extra):
        corpo = {"sessao": self.sessao.id, "texto": "Que filme!"}
        corpo.update(extra)
        return self.client.post("/api/comentarios/", corpo, format="multipart")

    def test_so_logados_veem_comentarios(self):
        self.assertEqual(self.client.get("/api/comentarios/").status_code, 401)
        self.entrar(self.beto)
        self.assertEqual(self.client.get("/api/comentarios/").status_code, 200)

    def test_autor_e_o_usuario_logado(self):
        self.entrar(self.beto)
        r = self.comentar(autor=self.ana.id)  # tentativa de se passar por outra pessoa
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["autor_apelido"], "Beto")
        self.assertTrue(r.data["pode_editar"])

    def test_usuario_sem_amigo_nao_comenta(self):
        self.entrar(self.admin)  # a admin ainda não tem um Amigo ligado
        self.assertEqual(self.comentar().status_code, 403)

    def test_comentario_com_fotos(self):
        self.entrar(self.beto)
        r = self.comentar(imagens=[imagem_png("a.png"), imagem_png("b.png", (0, 90, 200))])
        self.assertEqual(r.status_code, 201)
        self.assertEqual(len(r.data["fotos"]), 2)
        self.assertEqual(FotoComentario.objects.count(), 2)
        self.assertTrue(r.data["fotos"][0]["imagem"].startswith("http"))

    def test_limite_de_fotos_por_comentario(self):
        self.entrar(self.beto)
        fotos = [imagem_png(f"{i}.png") for i in range(5)]
        r = self.comentar(imagens=fotos)
        self.assertEqual(r.status_code, 400)
        self.assertIn("imagens", r.data)
        self.assertEqual(Comentario.objects.count(), 0)

    def test_arquivo_que_nao_e_imagem_e_recusado(self):
        self.entrar(self.beto)
        falso = SimpleUploadedFile("virus.png", b"isto nao e uma imagem", content_type="image/png")
        r = self.comentar(imagens=[falso])
        self.assertEqual(r.status_code, 400)
        self.assertIn("imagens", r.data)

    @override_settings(FOTO_TAMANHO_MAX_BYTES=50)
    def test_foto_grande_demais_e_recusada(self):
        self.entrar(self.beto)
        r = self.comentar(imagens=[imagem_png()])
        self.assertEqual(r.status_code, 400)
        self.assertIn("imagens", r.data)

    def test_so_o_dono_ou_a_admin_altera_o_comentario(self):
        self.entrar(self.beto)
        pk = self.comentar().data["id"]
        url = f"/api/comentarios/{pk}/"

        self.entrar(self.ana)
        self.assertEqual(self.client.patch(url, {"texto": "Editado"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)

        self.entrar(self.beto)
        r = self.client.patch(url, {"texto": "Editado por mim"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["texto"], "Editado por mim")

        self.entrar(self.admin)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_nao_muda_a_sessao_de_um_comentario(self):
        outra = self.nova_sessao(self.f2, self.beto, 8, "B")
        self.entrar(self.beto)
        pk = self.comentar().data["id"]
        r = self.client.patch(f"/api/comentarios/{pk}/", {"sessao": outra.id}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_apagar_foto_remove_o_registro_e_o_arquivo(self):
        self.entrar(self.beto)
        r = self.comentar(imagens=[imagem_png()])
        foto = FotoComentario.objects.get(pk=r.data["fotos"][0]["id"])
        caminho = foto.imagem.path

        self.entrar(self.ana)
        self.assertEqual(self.client.delete(f"/api/fotos/{foto.id}/").status_code, 403)

        self.entrar(self.beto)
        self.assertEqual(self.client.delete(f"/api/fotos/{foto.id}/").status_code, 204)
        self.assertFalse(FotoComentario.objects.filter(pk=foto.id).exists())
        with self.assertRaises(FileNotFoundError):
            open(caminho, "rb")


# ------------------------------------------------------------------- TMDB


def tmdb_falso(caminho, **params):
    """Respostas fixas no lugar do TMDB de verdade (os testes não usam a internet)."""
    if caminho == "/search/movie":
        return {"results": [{
            "id": 603, "title": "Matrix", "original_title": "The Matrix",
            "release_date": "1999-03-30", "overview": "Um hacker descobre a verdade.",
            "poster_path": "/matrix.jpg", "popularity": 50,
        }]}
    if caminho == "/search/tv":
        return {"results": [{
            "id": 1396, "name": "Breaking Bad", "original_name": "Breaking Bad",
            "first_air_date": "2008-01-20", "overview": "Um professor vira fabricante de drogas.",
            "poster_path": "/bb.jpg", "popularity": 80,
        }]}
    if caminho == "/movie/603":
        return {
            "title": "Matrix", "release_date": "1999-03-30",
            "overview": "Um hacker descobre a verdade.", "poster_path": "/matrix.jpg",
            "genres": [{"name": "Ação"}, {"name": "Ficção científica"}],
            "credits": {"crew": [
                {"job": "Director", "name": "Lana Wachowski"},
                {"job": "Director", "name": "Lilly Wachowski"},
                {"job": "Producer", "name": "Joel Silver"},
            ]},
        }
    if caminho == "/tv/1396":
        return {
            "name": "Breaking Bad", "first_air_date": "2008-01-20",
            "overview": "Um professor vira fabricante de drogas.", "poster_path": "/bb.jpg",
            "genres": [{"name": "Drama"}, {"name": "Crime"}],
            "created_by": [{"name": "Vince Gilligan"}],
        }
    if caminho == "/tv/603":  # uma série com o mesmo número do filme Matrix
        return {
            "name": "Outra Série", "first_air_date": "2015-05-05", "overview": "",
            "poster_path": None, "genres": [], "created_by": [],
        }
    raise tmdb.TMDBError("Título não encontrado no TMDB.")


class TMDBTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        patcher = patch("mural.tmdb._get", side_effect=tmdb_falso)
        self.falso = patcher.start()
        self.addCleanup(patcher.stop)

    def sessao_de_tmdb(self, tmdb_id, tipo=None, dias_atras=2, tier="S"):
        corpo = {
            "tmdb_id": tmdb_id, "sugerido_por": [self.ana.id],
            "data_exibicao": str(self.hoje - timedelta(days=dias_atras)), "tier": tier,
        }
        if tipo:
            corpo["tipo"] = tipo
        return self.client.post("/api/sessoes/", corpo, format="json")

    def test_busca_exige_login(self):
        self.assertEqual(self.client.get("/api/tmdb/buscar/?q=matrix").status_code, 401)

    def test_busca_traz_filmes_e_series_os_mais_populares_primeiro(self):
        self.entrar(self.ana)
        r = self.client.get("/api/tmdb/buscar/?q=matrix&ano=1999")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([i["tipo"] for i in r.data], ["serie", "filme"])
        serie, filme = r.data
        self.assertEqual(serie["titulo"], "Breaking Bad")
        self.assertEqual(serie["ano_lancamento"], 2008)
        self.assertEqual(filme["tmdb_id"], 603)
        self.assertEqual(filme["ano_lancamento"], 1999)
        self.assertEqual(filme["poster_url"], "https://image.tmdb.org/t/p/w500/matrix.jpg")

    def test_busca_curta_demais(self):
        self.entrar(self.ana)
        self.assertEqual(self.client.get("/api/tmdb/buscar/?q=m").status_code, 400)

    def test_sessao_criada_com_tmdb_id_salva_o_filme_com_todos_os_dados(self):
        self.entrar(self.ana)
        r = self.sessao_de_tmdb(603)
        self.assertEqual(r.status_code, 201)
        filme = Filme.objects.get(tmdb_id=603)
        self.assertEqual(filme.tipo, "filme")
        self.assertEqual(filme.titulo, "Matrix")
        self.assertEqual(filme.ano_lancamento, 1999)
        self.assertEqual(filme.genero, "Ação, Ficção científica")
        self.assertEqual(filme.diretor, "Lana Wachowski, Lilly Wachowski")
        self.assertEqual(r.data["filme_detalhe"]["sinopse"], "Um hacker descobre a verdade.")

    def test_sessao_com_serie_usa_os_criadores_e_o_ano_de_estreia(self):
        self.entrar(self.ana)
        r = self.sessao_de_tmdb(1396, tipo="serie")
        self.assertEqual(r.status_code, 201)
        serie = Filme.objects.get(tmdb_id=1396)
        self.assertEqual(serie.tipo, "serie")
        self.assertEqual(serie.titulo, "Breaking Bad")
        self.assertEqual(serie.ano_lancamento, 2008)
        self.assertEqual(serie.diretor, "Vince Gilligan")
        self.assertEqual(serie.genero, "Drama, Crime")
        self.assertEqual(r.data["filme_detalhe"]["tipo"], "serie")
        self.assertEqual(r.data["filme_titulo"], "Breaking Bad")

    def test_filme_e_serie_com_o_mesmo_numero_convivem(self):
        self.entrar(self.ana)
        self.assertEqual(self.sessao_de_tmdb(603, dias_atras=20).status_code, 201)
        self.assertEqual(self.sessao_de_tmdb(603, tipo="serie", dias_atras=10).status_code, 201)
        self.assertEqual(Filme.objects.filter(tmdb_id=603).count(), 2)
        self.assertEqual(
            sorted(Filme.objects.filter(tmdb_id=603).values_list("tipo", flat=True)),
            ["filme", "serie"],
        )

    def test_tipo_invalido_retorna_400(self):
        self.entrar(self.ana)
        r = self.sessao_de_tmdb(603, tipo="documentario")
        self.assertEqual(r.status_code, 400)
        self.assertIn("tipo", r.data)

    def test_titulo_ja_conhecido_nao_e_buscado_de_novo(self):
        self.entrar(self.ana)
        for dias in (20, 5):
            self.assertEqual(self.sessao_de_tmdb(603, dias_atras=dias, tier="A").status_code, 201)
        self.assertEqual(Filme.objects.filter(tmdb_id=603).count(), 1)
        consultas = [c for c in self.falso.call_args_list if c.args[0] == "/movie/603"]
        self.assertEqual(len(consultas), 1)

    def test_tmdb_id_inexistente_vira_erro_de_validacao(self):
        self.entrar(self.ana)
        r = self.sessao_de_tmdb(999999)
        self.assertEqual(r.status_code, 400)
        self.assertIn("tmdb_id", r.data)


class TMDBSemChaveTests(BaseTestCase):
    @override_settings(TMDB_API_KEY="")
    def test_busca_sem_chave_configurada_avisa(self):
        self.entrar(self.ana)
        r = self.client.get("/api/tmdb/buscar/?q=matrix")
        self.assertEqual(r.status_code, 502)
        self.assertIn("não está configurada", r.data["detail"])


# ------------------------------------------------- importador do histórico


def filme_tmdb(pk, titulo, data, votos=10, original=None):
    return {
        "id": pk, "title": titulo, "original_title": original or titulo, "release_date": data,
        "overview": "", "poster_path": None, "popularity": votos, "vote_count": votos,
    }


CATALOGO = [
    filme_tmdb(603, "Matrix", "1999-03-30", 9000, "The Matrix"),
    filme_tmdb(10625, "Meninas Malvadas", "2004-04-30", 900, "Mean Girls"),
    filme_tmdb(673593, "Meninas Malvadas", "2024-01-10", 800, "Mean Girls"),
    filme_tmdb(508442, "Soul", "2020-12-25", 9000),
    filme_tmdb(777, "Soul", "2020-05-05", 2),
    filme_tmdb(187, "Sin City: A Cidade do Pecado", "2005-04-01", 500, "Sin City"),
    filme_tmdb(555, "Obsessão", "2025-09-05", 300, "Obsession"),
    filme_tmdb(120, "La La Land: Cantando Estações", "2016-11-29", 900, "La La Land: X"),
]


def tmdb_catalogo(caminho, **params):
    """Um TMDB de mentira que procura no CATALOGO (pelo nome e pelo ano)."""
    if caminho == "/search/movie":
        texto = params["query"].lower()
        # O TMDB também aceita o ano de relançamentos e estreias em outros países.
        return {"results": [
            f for f in CATALOGO
            if texto in (f["title"] + f["original_title"]).lower()
            and params.get("year") in (None, int(f["release_date"][:4]))
        ]}
    if caminho == "/search/tv":
        return tmdb_falso(caminho) if "breaking" in params["query"].lower() else {"results": []}
    for f in CATALOGO:
        if caminho == f"/movie/{f['id']}":
            return {**f, "genres": [], "credits": {"crew": []}}
    return tmdb_falso(caminho, **params)


@override_settings(TMDB_API_KEY="chave-de-teste")
class ImportadorTests(BaseTestCase):
    CABECALHO = "ano;titulo;tipo;tier;indicado_por;data;ano_lancamento;tmdb_id"

    def setUp(self):
        super().setUp()
        patcher = patch("mural.tmdb._get", side_effect=tmdb_catalogo)
        self.falso = patcher.start()
        self.addCleanup(patcher.stop)
        pasta = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, pasta, ignore_errors=True)
        self.caminho = os.path.join(pasta, "lista.csv")

    def lista(self, *linhas, cabecalho=CABECALHO, codificacao="utf-8-sig"):
        with open(self.caminho, "w", encoding=codificacao) as arquivo:
            arquivo.write("\n".join([cabecalho, *linhas]) + "\n")

    def ler_lista(self):
        with open(self.caminho, encoding="utf-8-sig") as arquivo:
            return arquivo.read()

    def importar(self, **opcoes):
        saida = io.StringIO()
        call_command("importar_historico", self.caminho, stdout=saida, no_color=True, **opcoes)
        return saida.getvalue()

    def conferir(self, *respostas):
        """Roda a conferência respondendo às perguntas (sem respostas, só lista)."""
        if not respostas:
            return self.importar(conferir=True, sem_perguntas=True)
        comando = "mural.management.commands.importar_historico"
        with (
            patch(f"{comando}.Command._pode_perguntar", return_value=True),
            patch("builtins.input", side_effect=respostas),
        ):
            return self.importar(conferir=True)

    def assertNadaGravado(self):
        self.assertEqual(Sessao.objects.count(), 0)
        self.assertEqual(Filme.objects.count(), 3)  # só os do setUp
        self.assertEqual(Amigo.objects.count(), 2)

    def assertFalha(self, trecho):
        saida = io.StringIO()
        with self.assertRaises(CommandError) as contexto:
            call_command("importar_historico", self.caminho, stdout=saida, no_color=True)
        self.assertIn(trecho, saida.getvalue() + str(contexto.exception))
        self.assertNadaGravado()

    # Importação

    def test_importa_titulos_sessoes_e_indicadores(self):
        self.lista(
            "2024;Matrix;filme;s;ana+Le;;1999;",
            "2025;Breaking Bad;Série;A;Le;;;",
            "2026;Sin City;filme;VTNC;Beto;2026-01-03;2005;",
        )
        self.assertIn("3 sessão(ões)", self.importar())

        s = Sessao.objects.get(filme__tmdb_id=603)
        self.assertEqual((s.ano, s.data_exibicao, s.tier, s.criado_por), (2024, None, "S", None))
        # "ana" é a Ana que já existia; "Le" é criado uma vez só, sem ícone.
        self.assertEqual({a.apelido for a in s.sugerido_por.all()}, {"Ana", "Le"})
        self.assertEqual(Amigo.objects.get(apelido="Le").icone_url, "")
        self.assertEqual(Amigo.objects.count(), 3)

        self.assertEqual(Sessao.objects.get(filme__tipo="serie").filme.tmdb_id, 1396)
        com_data = Sessao.objects.get(filme__tmdb_id=187)
        self.assertEqual((com_data.ano, com_data.data_exibicao), (2026, date(2026, 1, 3)))

    def test_importar_de_novo_nao_duplica(self):
        self.lista("2024;Matrix;filme;S;Ana;;;", "2026;Soul;filme;A;Ana;2026-01-03;2020;")
        self.importar()
        self.assertIn("2 já estava(m) no site", self.importar())
        self.assertEqual(Sessao.objects.count(), 2)

    def test_titulo_revisto_entra_uma_vez_por_linha(self):
        self.lista("2024;Matrix;filme;S;Ana;;;", "2024;Matrix;filme;A;Ana;;;")
        self.assertIn("reviu", self.conferir())
        self.importar()
        self.importar()
        self.assertEqual(Sessao.objects.count(), 2)

    def test_tmdb_id_forca_o_titulo(self):
        self.lista("2024;Nome qualquer;filme;S;Ana;;;10625")
        self.importar()
        self.assertEqual(Sessao.objects.get().filme.titulo, "Meninas Malvadas")

    def test_data_no_formato_do_excel(self):
        self.lista("2026;Matrix;filme;S;Ana;15/02/2026;;")
        self.importar()
        self.assertEqual(Sessao.objects.get().data_exibicao, date(2026, 2, 15))

    def test_lista_sem_as_colunas_opcionais(self):
        self.lista("2024;Matrix;filme;S;Ana", cabecalho="ano;titulo;tipo;tier;indicado_por")
        self.importar()
        self.assertEqual(Sessao.objects.count(), 1)

    def test_falha_no_meio_nao_grava_nada(self):
        self.lista("2024;Matrix;filme;S;Ana;;;", "2024;Soul;filme;S;Novato;;2020;")

        def falha_no_soul(caminho, **params):
            if caminho == "/movie/508442":
                raise tmdb.TMDBError("Não foi possível consultar o TMDB agora.")
            return tmdb_catalogo(caminho, **params)

        self.falso.side_effect = falha_no_soul
        self.assertFalha("Nada foi gravado")

    # Regras

    def test_linhas_com_problema_impedem_a_importacao(self):
        certa = "2024;Matrix;filme;S;Ana;;;"
        ano_atual = self.hoje.year
        amanha = self.hoje + timedelta(days=1)
        casos = [
            ("2024;Soul;filme;;Ana;;2020;", "precisa ter tier"),
            ("2024;Soul;filme;D;Ana;;2020;", "tier deve ser"),
            ("2024;Soul;curta;A;Ana;;2020;", "tipo deve ser"),
            ("2024;Soul;filme;A;;;2020;", "pelo menos um amigo"),
            ("2024;Soul;filme;A;X;;2020;", "apelido"),
            ("2023;Soul;filme;A;Ana;;2020;", "O grupo começou em 2024"),
            (f"{ano_atual};Soul;filme;A;Ana;;2020;", "Só anos anteriores"),
            ("2024;Soul;filme;A;Ana;2025-01-01;2020;", "mesmo da data"),
            (f"{amanha.year};Soul;filme;A;Ana;{amanha};2020;", "já aconteceu"),
            ("2024;Soul;filme;A;Ana;ontem;2020;", "data inválido"),
            ("dois mil;Soul;filme;A;Ana;;2020;", "ano inválido"),
            ("2024;Soul;filme;A;Ana", "quantidade de campos"),
            ("2024;Soul;filme;A;Ana;;2020;;;", "quantidade de campos"),
            ("2024;Título Que Não Existe;filme;A;Ana;;;", "Nada encontrado"),
            ("2024;Soul;filme;A;Ana;;;999999", "não encontrado no TMDB"),
        ]
        for linha, trecho in casos:
            with self.subTest(linha=linha):
                self.lista(certa, linha)
                self.assertFalha(trecho)

    def test_uma_sessao_por_data(self):
        self.lista("2026;Matrix;filme;S;Ana;2026-01-03;;", "2026;Soul;filme;S;Ana;2026-01-03;2020;")
        self.assertFalha("mais de um título em 03/01/2026")

    def test_data_ocupada_no_site(self):
        self.criar_sessao(self.f1, [self.ana], date(2026, 1, 3), "S")
        self.lista("2026;Matrix;filme;S;Ana;2026-01-03;;")
        self.assertIn("Já existe no site uma sessão em 03/01/2026: Pulp Fiction", self.conferir())
        with self.assertRaises(CommandError):
            self.importar()
        self.assertEqual(Sessao.objects.count(), 1)

    def test_arquivo_invalido(self):
        for linhas, opcoes, trecho in (
            (["2024;Matrix"], {"cabecalho": "ano;titulo"}, "falta a coluna"),
            (["2024;Obsessão;filme;S;Ana;;;"], {"codificacao": "cp1252"}, "UTF-8"),
            ([], {}, "vazia"),
        ):
            with self.subTest(trecho=trecho):
                self.lista(*linhas, **opcoes)
                self.assertFalha(trecho)
        self.caminho += ".sumiu"
        self.assertFalha("não encontrado")

    @override_settings(TMDB_API_KEY="")
    def test_sem_chave_do_tmdb_avisa(self):
        self.lista("2024;Matrix;filme;S;Ana;;;")
        self.assertFalha("TMDB_API_KEY")

    def test_chave_recusada_para_na_primeira_consulta(self):
        self.lista("2024;Matrix;filme;S;Ana;;;", "2024;Soul;filme;S;Ana;;;")
        self.falso.side_effect = tmdb.TMDBChaveError("O TMDB recusou a chave de acesso.")
        self.assertFalha("Confira a TMDB_API_KEY")
        self.assertEqual(self.falso.call_count, 1)

    # Escolha do título

    def test_titulo_ambiguo_impede_a_importacao(self):
        self.lista("2024;Meninas Malvadas;filme;S;Ana;;;")
        self.assertFalha("Falta escolher (1)")

    def test_ano_de_lancamento_desempata(self):
        self.lista("2024;Meninas Malvadas;filme;S;Ana;;2004;")
        self.importar()
        self.assertEqual(Sessao.objects.get().filme.tmdb_id, 10625)

    def test_homonimo_desconhecido_e_avisado(self):
        self.lista("2024;Soul;filme;S;Ana;;2020;")
        saida = self.conferir()
        self.assertIn("mas confira (1)", saida)
        self.assertIn("movie/508442", saida)

    def test_estreia_um_ano_antes_e_aceita_com_aviso(self):
        self.lista("2026;Obsessão;filme;S;Ana;2026-07-04;2026;")
        self.assertIn("ano diferente do informado", self.conferir())

    def test_ano_muito_diferente_pede_escolha(self):
        self.lista("2024;Matrix;filme;S;Ana;;2021;")
        self.assertIn("Falta escolher (1)", self.conferir())

    def test_nome_parcial_com_um_so_resultado_e_avisado(self):
        self.lista("2024;La La Land;filme;S;Ana;;2016;")
        self.assertIn("nome diferente, único resultado", self.conferir())

    # Conferência

    def test_conferir_nao_grava_no_banco_nem_na_lista(self):
        self.lista("2024;Matrix;filme;S;Novato;;1999;")
        antes = self.ler_lista()
        saida = self.conferir()
        self.assertIn("Tudo certo", saida)
        self.assertIn("Amigos novos: Novato", saida)
        self.assertNadaGravado()
        self.assertEqual(self.ler_lista(), antes)

    def test_escolha_pelo_numero_fica_na_lista(self):
        self.lista("2024;Meninas Malvadas;filme;S;Ana;;;", "2024;Matrix;filme;A;Beto;;;")
        saida = self.conferir("9", "abc", "2")
        self.assertEqual(saida.count("Opção inválida"), 2)
        self.assertIn("Tudo certo", saida)
        self.assertIn("2024;Meninas Malvadas;filme;S;Ana;;;673593\n", self.ler_lista())
        self.assertIn("2024;Matrix;filme;A;Beto;;;\n", self.ler_lista())
        self.assertNadaGravado()
        self.importar()
        self.assertTrue(Sessao.objects.filter(filme__tmdb_id=673593).exists())

    def test_escolha_por_outro_id(self):
        self.lista(
            "2024;Meninas Malvadas;filme;S;Ana", cabecalho="ano;titulo;tipo;tier;indicado_por"
        )
        self.conferir("id 999999", "id 603")  # o primeiro não existe e é recusado
        self.assertIn("indicado_por;tmdb_id\n", self.ler_lista())
        self.assertIn("2024;Meninas Malvadas;filme;S;Ana;603\n", self.ler_lista())

    def test_pular_ou_sair_deixa_pendente(self):
        for resposta in ("", "s"):
            with self.subTest(resposta=resposta):
                self.lista("2024;Meninas Malvadas;filme;S;Ana;;;")
                self.assertIn("Falta escolher (1)", self.conferir(resposta))
        self.assertNadaGravado()

    def test_salvar_a_escolha_nao_perde_campos_de_linha_com_erro(self):
        self.lista("2024;Meninas Malvadas;filme;S;Ana;;;", "2024;Soul;filme;A;Ana;;2020;;sobra")
        self.conferir("1")
        self.assertIn("2024;Soul;filme;A;Ana;;2020;;sobra\n", self.ler_lista())


# ---------------------------------------------------------- documentação


class DocumentacaoTests(BaseTestCase):
    def test_schema_openapi_e_gerado(self):
        r = self.client.get("/api/schema/")
        self.assertEqual(r.status_code, 200)
