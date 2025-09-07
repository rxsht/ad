import logging
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from ldap3 import Server, Connection, ALL, SUBTREE

logger = logging.getLogger(__name__)
User = get_user_model()


class LDAPBackend(BaseBackend):
    LDAP_SERVER_URI = 'ldaps://ldap.bsuir.by'
    LDAP_BIND_DN = 'uid=smdoadmin,ou=staff,dc=bsuir,dc=by'
    LDAP_BIND_PASSWORD = 'eW308687!'
    LDAP_USER_SEARCH_BASES = [
        'ou=staff,dc=bsuir,dc=by',
        'ou=stud,dc=bsuir,dc=by'
    ]
    LDAP_USER_FILTER = '(uid={username})'
    LDAP_ATTRIBUTE_MAP = {
        "first_name": "givenName",
        "last_name": "sn",
        "email": "mail",
        "username": "uid",
    }

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            logger.warning("LDAP: Не указаны имя пользователя или пароль")
            return None

        server = Server(self.LDAP_SERVER_URI, get_info=ALL)

        try:
            with Connection(server, self.LDAP_BIND_DN, self.LDAP_BIND_PASSWORD, auto_bind=True) as admin_conn:
                for base_dn in self.LDAP_USER_SEARCH_BASES:
                    search_filter = self.LDAP_USER_FILTER.format(username=username)
                    logger.debug(f"LDAP: Поиск {username} в {base_dn} с фильтром {search_filter}")
                    admin_conn.search(
                        search_base=base_dn,
                        search_filter=search_filter,
                        search_scope=SUBTREE,
                        attributes=list(self.LDAP_ATTRIBUTE_MAP.values()) + ['ourMail', 'maildrop']
                    )

                    if admin_conn.entries:
                        ldap_entry = admin_conn.entries[0]
                        user_dn = ldap_entry.entry_dn
                        logger.debug(f"LDAP: Найден DN пользователя: {user_dn}")

                        with Connection(server, user_dn, password, auto_bind=True):
                            logger.info(f"LDAP: Успешная авторизация {username}")
                            return self._get_or_create_user(username, ldap_entry)

                logger.warning(f"LDAP: Пользователь {username} не найден")
                return None

        except Exception as e:
            logger.error(f"Ошибка при подключении к LDAP: {e}")
            return None

    
    def _get_or_create_user(self, username, ldap_entry):
        user, created = User.objects.get_or_create(username=username)
    
        for field, attr in self.LDAP_ATTRIBUTE_MAP.items():
            if hasattr(user, field) and attr in ldap_entry:
                setattr(user, field, ldap_entry[attr].value)
    
        # email логика: пытаемся вытащить из нестандартных полей
        email = None
        if 'ourMail' in ldap_entry:
            email = ldap_entry['ourMail'].value
            logger.info(f"LDAP: Email найден через ourMail → {email}")
        elif 'maildrop' in ldap_entry:
            email = ldap_entry['maildrop'].value
            logger.info(f"LDAP: Email найден через maildrop → {email}")
        else:
            logger.warning(f"LDAP: Email не найден в LDAP для {username}, будет установлена заглушка")
    
        # Ставим email вручную (обязательно)
        if not email:
            email = f'{username}@bsuir.by'
    
        setattr(user, 'email', email)
    
        # Завершаем сохранение
        user.set_unusable_password()
        user.save()
        return user


#    def _get_or_create_user(self, username, ldap_entry):
#        user, created = User.objects.get_or_create(username=username)
#
#        for field, attr in self.LDAP_ATTRIBUTE_MAP.items():
#            if hasattr(user, field) and attr in ldap_entry:
#                setattr(user, field, ldap_entry[attr].value)

        # временная заглушка на email, потому что не берется из ldap сервера, а он NOT NULL, хочу проверить без этого
#        if not getattr(user, 'email', None):
#           setattr(user, 'email', f'{username}@bsuir.by')
#            logger.warning(f"LDAP: Email не найден для {username}, установлен заглушка")
#
#        user.set_unusable_password()
#        user.save()
#        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
