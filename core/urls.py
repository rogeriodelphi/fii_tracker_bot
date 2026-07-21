from django.contrib import admin
from django.urls import path
from bot.views import (
    home,
    cadastrar_ativo,
    editar_ativo,
    excluir_ativo,
    importar_carteira  # <--- 1. Importação adicionada aqui
)

urlpatterns = [
    path('admin/',                 admin.site.urls),
    path('',                       home,             name='home'),
    path('ativos/novo/',           cadastrar_ativo,  name='cadastrar_ativo'),
    path('ativos/importar/',       importar_carteira, name='importar_carteira'),  # <--- 2. Rota adicionada aqui
    path('ativos/<int:pk>/editar/', editar_ativo,     name='editar_ativo'),
    path('ativos/<int:pk>/excluir/',excluir_ativo,    name='excluir_ativo'),
]