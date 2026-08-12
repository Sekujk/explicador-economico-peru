"""Precios de commodities vía yfinance (sin API key)."""

from datetime import date, timedelta

import yfinance as yf


def fetch_series(ticker: str, fecha_inicio: date, fecha_fin: date) -> list[tuple[date, float]]:
    """Descarga el precio de cierre diario de un ticker y lo devuelve como (fecha, valor).

    yfinance trata `end` como exclusivo, así que se le suma un día para incluir
    `fecha_fin` en el rango.
    """
    hist = yf.Ticker(ticker).history(
        start=fecha_inicio.isoformat(),
        end=(fecha_fin + timedelta(days=1)).isoformat(),
    )

    return [
        (indice.date(), float(fila["Close"]))
        for indice, fila in hist.iterrows()
    ]
