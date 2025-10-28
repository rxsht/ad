from django.shortcuts import redirect, render
from django.contrib import auth, messages
from users.forms import UserLoginForm
from django.http import HttpResponseRedirect 
from django.urls import reverse
from users.models import User  
from .utils import q_search
from django.contrib.auth import logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required


def main(request):
    if request.method=='POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            username = request.POST['username']
            password = request.POST['password']
            user = auth.authenticate(username=username, password=password)
            if user:
                auth.login(request, user)
                return HttpResponseRedirect(reverse('documents:cabinet'))
    else:
        form=UserLoginForm()
    context={
        'form' : form, 
    }
    return render(request, 'users/main.html', context)

"""def logout_view(request):
    logout(request)
    return redirect(reverse('main'))"""

@login_required
def pers_cab(request):
    
    context={
        
    }
    return render(request, 'users/pers-cab.html', context)


 

@login_required
def logout_view(request):
    messages.success(request, f"{request.user.username}, Вы вышли из аккаунта")
    auth.logout(request)
    return render(request, 'users/main.html')
