#!/usr/bin/env python3
"""Fail closed unless Azure spending protection and recent verified credit cover the budget.

The review file records an observed balance; it never replaces the operator's
explicit deployment approval or creates an automatic billing cutoff.
"""
import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from azure_snapshot import request


def validate_credit(subscription, review, subscription_id, budget, now=None):
    now = now or datetime.now(timezone.utc)
    if subscription.get("subscriptionId", "").lower() != subscription_id.lower():
        raise ValueError("La respuesta no corresponde a la suscripción aprobada")
    if subscription.get("state") != "Enabled":
        raise ValueError("La suscripción no está activa")
    limit = (subscription.get("subscriptionPolicies") or {}).get("spendingLimit")
    if limit != "On":
        raise ValueError(f"No se confirmó protección de gasto On (Azure devuelve {limit!r}); no se crea nada")
    if review.get("subscription_id", "").lower() != subscription_id.lower():
        raise ValueError("La revisión del saldo pertenece a otra suscripción")
    observed = datetime.fromisoformat(review["reviewed_at_utc"])
    if observed.tzinfo is None or not timedelta(0) <= now - observed <= timedelta(hours=24):
        raise ValueError("La revisión del crédito debe tener menos de 24 horas y hora UTC válida")
    if date.fromisoformat(review["expires_on"]) <= now.date():
        raise ValueError("Crédito vencido o que vence hoy; revisar antes de desplegar")
    amount = Decimal(str(budget))
    available = Decimal(str(review["available_lower_bound_usd"]))
    if not amount.is_finite() or not available.is_finite() or amount <= 0 or available < amount:
        raise ValueError("El presupuesto debe ser positivo y estar cubierto por el crédito verificado")
    return {"spending_limit": limit, "credit_covers_approved_budget": True,
            "notice": "No se cambió facturación. El presupuesto registrado no es un corte automático."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--budget-usd", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        subscription_id = os.environ["CAFENUBE_SUBSCRIPTION_ID"]
        metadata = request("rest", "--method", "get", "--uri", "/subscriptions/" + subscription_id,
                           "--url-parameters", "api-version=2022-12-01")
        (args.output / "subscription-policy.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        review = json.loads(args.review.read_text("utf-8"))
        result = validate_credit(metadata, review, subscription_id, args.budget_usd)
        (args.output / "credit-guard.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("Protección de gasto On y crédito suficiente para el presupuesto aprobado: comprobados.")
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, InvalidOperation) as error:
        print(f"DETENIDO por protección de costos: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
