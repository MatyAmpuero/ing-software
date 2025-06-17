def roles(request):
    """
    Añade a todos los templates booleanos sobre el rol actual del usuario.
    """
    ctx = {}
    user = request.user
    if user.is_authenticated:
        grupos = set(user.groups.values_list('name', flat=True))
        ctx['es_jefe']      = 'Jefe'      in grupos
        ctx['es_bodeguero'] = 'Bodeguero' in grupos
        ctx['es_cajero']    = 'Cajero'    in grupos
    return ctx