from django.contrib import admin
from django.urls import path
from bot.views import home # Importe sua view aqui

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'), # Página inicial do site
]
