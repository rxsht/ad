from django.db.models import Q
from users.models import User

def q_search(query):
    search_terms = query.split()  
    q_objects = Q() 

    for term in search_terms:
        q_objects |= Q(first_name__icontains=term) | Q(last_name__icontains=term) | Q(sur_name__icontains=term)

    return User.objects.filter(q_objects)
