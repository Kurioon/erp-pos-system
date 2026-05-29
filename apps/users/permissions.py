from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminRole(BasePermission):
    """
    Дозволяє доступ лише користувачам з роллю 'admin'.
    Використовувати для ендпоінтів, куди касирам вхід суворо заборонено (наприклад, Закупівлі, Створення товарів).
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')


class IsSellerRole(BasePermission):
    """
    Дозволяє доступ лише користувачам з роллю 'seller'.
    Використовувати для специфічних операцій продавця (наприклад, особиста каса).
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'seller')


class IsAdminOrReadOnly(BasePermission):
    """
    Дозволяє читати дані всім авторизованим (і адмінам, і продавцям), 
    але створювати/видаляти/редагувати - ТІЛЬКИ адміністраторам.
    Ідеально підходить для каталогу товарів (Product).
    """
    def has_permission(self, request, view):
        # Якщо це безпечний метод (GET, HEAD, OPTIONS) - пускаємо всіх авторизованих
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        
        # Якщо це POST, PUT, PATCH, DELETE - пускаємо тільки адмінів
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')