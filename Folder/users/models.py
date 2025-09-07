from django.db import models
from django.contrib.auth.models import AbstractUser




# Create your models here.

class User(AbstractUser):
    sur_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='отчество')
    image= models.ImageField(upload_to='user_image',blank=True, null=True, verbose_name='Аватар')
    class Meta:
        db_table: 'User'
        verbose_name: str= 'Пользователь'
        verbose_name_plural: str= 'Пользователи'

    def __str__ (self):
        return self.username
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
