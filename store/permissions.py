from rest_framework import permissions

class IsSuperUser(permissions.BasePermission):
    """
    Custom permission to allow only superusers to access.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)
