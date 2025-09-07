from django import forms
from documents.models import Document
from documents.models import Status
from documents.models import Type



class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['name', 'result', 'data', 'status','type']
        widgets = {
           'status': forms.HiddenInput(),  # Скрываем поле parent в форме
         }


    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
        # self.fields['status'].initial = 1
    # def __init__(self, *args, **kwargs):
    #     super(DocumentForm, self).__init__(*args, **kwargs)
    #     if not self.instance.pk:  # Проверяем, что экземпляр еще не сохранен в базу данных
    #          self.fields['status'].initial = 1  # Устанавливаем значение по умолчанию для поля parent