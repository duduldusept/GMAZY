from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('interventions.urls')),
    path('utilisateurs/', include('utilisateurs.urls')),
    path('machines/', include('machines.urls')),
]  # <--- Ce crochet ferme proprement la liste urlpatterns

# --- PERSONNALISATION DU TITRE DE L'ADMINISTRATION ---
admin.site.site_header = "Gmazy"
admin.site.site_title = "Gmazy Admin"
admin.site.index_title = "Tableau de bord"
