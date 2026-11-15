"""HTTP routes of the AstroHealth API (docs/api_contract.md section 4)."""

from app.routes import alerts, astronauts, journal, readings

ROUTERS = (astronauts.router, readings.router, journal.router, alerts.router)
