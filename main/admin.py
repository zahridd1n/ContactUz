from django.contrib import admin
from . import models

admin.site.register(models.Region)
admin.site.register(models.District)
admin.site.register(models.Business)
admin.site.register(models.BusinessCategory)
# admin.site.register(models.UserRegion)
admin.site.register(models.ContactUs)