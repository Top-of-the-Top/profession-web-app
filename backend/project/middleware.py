import time
import sys


class Term:
    GRAY = '\033[90m'
    CYAN = '\033[36m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        response = self.get_response(request)
        duration = time.perf_counter() - start

        status = response.status_code
        if status < 400:
            status_color = Term.GREEN
        elif status < 500:
            status_color = Term.YELLOW
        else:
            status_color = Term.RED

        time_color = Term.MAGENTA
        if duration > 0.5:
            time_color = Term.RED + Term.BOLD

        log_entry = (
            f"{Term.GRAY}{Term.RESET}{Term.YELLOW}SYNC{Term.RESET}{Term.GRAY}{Term.RESET} "
            f"{Term.GRAY}│{Term.RESET} {Term.WHITE}{Term.BOLD}{request.method:<7}{Term.RESET} "
            f"{Term.GRAY}│{Term.RESET} {Term.CYAN}{request.path:<40}{Term.RESET} "
            f"{Term.GRAY}│{Term.RESET} {status_color}{status:<3}{Term.RESET} "
            f"{Term.GRAY}│{Term.RESET} {time_color}{duration:.4f}s{Term.RESET}"
        )

        sys.stdout.write(log_entry + '\n')
        sys.stdout.flush()

        return response