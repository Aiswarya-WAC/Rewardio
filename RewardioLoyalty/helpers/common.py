from django.http import JsonResponse
from rest_framework import status

def error_response(errors={}, error_message='error', status=status.HTTP_500_INTERNAL_SERVER_ERROR, exception_info = None, **kwargs):
    response_data = {'status': False, 'message': error_message, 'errors': errors, "exception_info": exception_info, 'additional_info':kwargs}
    return JsonResponse(response_data, status=status)