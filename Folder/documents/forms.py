from django import forms
from documents.models import Document
from documents.models import Status
from documents.models import Type
from datetime import datetime



class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['name', 'result', 'data', 'status','type']
        widgets = {
           'status': forms.HiddenInput(),  # Скрываем поле parent в форме
         }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Проверяем, существует ли документ с таким названием
            if Document.objects.filter(name=name).exists():
                # Добавляем временную метку к названию
                timestamp = datetime.now().strftime("%d%m%y_%H%M")
                name = f"{name}_{timestamp}"
        return name


    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
        # self.fields['status'].initial = 1
    # def __init__(self, *args, **kwargs):
    #     super(DocumentForm, self).__init__(*args, **kwargs)
    #     if not self.instance.pk:  # Проверяем, что экземпляр еще не сохранен в базу данных
    #          self.fields['status'].initial = 1  # Устанавливаем значение по умолчанию для поля parent