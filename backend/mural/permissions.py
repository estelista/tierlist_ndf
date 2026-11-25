from rest_framework import permissions


class LeituraPublicaEscritaAutenticada(permissions.BasePermission):
    """Qualquer visitante lê; para criar, alterar ou apagar é preciso estar logado."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)


class LeituraPublicaEscritaAdmin(permissions.BasePermission):
    """Qualquer visitante lê; só a administradora (is_staff) altera."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class DonoOuAdmin(LeituraPublicaEscritaAutenticada):
    """Para alterar ou apagar um objeto é preciso ser o dono dele ou a administradora.

    O objeto precisa expor ``dono_id`` (o id do usuário que o criou).
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        return obj.dono_id is not None and obj.dono_id == request.user.id
