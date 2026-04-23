from rest_framework.response import Response

def process_error_response(exc):
    payload = {
        'status': 'error',
        'code': exc.code,
        'message': exc.message,
        'details': exc.details or {},
    }

    return Response(payload, status=exc.status)