from django.contrib import admin

from documents.models import Status, Document,Type


admin.site.register(Status)
#admin.site.register(Document)
admin.site.register(Type)