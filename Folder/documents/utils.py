from django.db.models import Q
from documents.models import Document


def q_search(query, user):
    keywords = query.split()
    q_objects = Q()

    for token in keywords:
        q_objects |= Q(name__icontains=token)

    return Document.objects.filter(q_objects, user=user)


def q_search_by_fio(query):

    search_terms = query.split() 
    q_objects = Q()  

    for term in search_terms:
        q_objects |= Q(user__first_name__icontains=term) | Q(user__last_name__icontains=term) | Q(user__sur_name__icontains=term)

    return Document.objects.filter(q_objects)