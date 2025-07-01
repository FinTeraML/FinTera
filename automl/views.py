import yfinance as yf
from django.http import JsonResponse

def get_stock_data(request):
    ticker = request.GET.get("ticker", "GOOG")
    data = yf.download(ticker, period="1y")

    close_series = data["Close"].dropna()

    close_dict = {
        str(date): float(price.values[0]) if hasattr(price, "values") else float(price)
        for date, price in close_series.items()
    }

    return JsonResponse(close_dict)
