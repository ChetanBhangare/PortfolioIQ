from app.data.providers.yahoo import YahooFinanceProvider
def get_market_provider(settings):
    if settings.market_data_provider.lower()=="yahoo": return YahooFinanceProvider()
    raise ValueError(f"Unsupported provider: {settings.market_data_provider}")
