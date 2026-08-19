"""
logic.py

Lógica de negocio del caso de uso de industria: un servicio de renta de
autos (car rental agency). Esto es lo que el servidor MCP expone como
"herramientas" (tools) para que un chatbot pueda:
    - Buscar autos disponibles según categoría/capacidad/presupuesto.
    - Consultar el detalle de un auto.
    - Crear una reservación.
    - Cancelar una reservación.
    - Listar las reservaciones existentes.

Este módulo NO sabe nada de JSON-RPC ni de transporte: es reutilizado
tanto por el servidor local (stdio) como por el servidor remoto (HTTP),
que sí implementan el protocolo MCP de forma manual.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List

_CATALOG_PATH = os.path.join(os.path.dirname(__file__), "catalog.json")

# Estado en memoria (para una demo; en producción sería una base de datos)
_reservations: Dict[str, dict] = {}


def _load_catalog() -> List[dict]:
    with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


CATALOG = _load_catalog()


# --------------------------------------------------------------------------
# Definición de las herramientas (equivalente a lo que tools/list retorna)
# --------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "search_cars",
        "description": (
            "Busca autos disponibles en el catálogo de la agencia de renta. "
            "Permite filtrar por categoría (economico, sedan, suv, van, lujo), "
            "número mínimo de asientos y precio máximo por día en USD."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["economico", "sedan", "suv", "van", "lujo"],
                    "description": "Categoría del vehículo",
                },
                "min_seats": {"type": "integer", "description": "Número mínimo de asientos"},
                "max_price_per_day": {"type": "number", "description": "Precio máximo por día en USD"},
            },
            "required": [],
        },
    },
    {
        "name": "get_car_details",
        "description": "Obtiene el detalle completo de un auto dado su id.",
        "inputSchema": {
            "type": "object",
            "properties": {"car_id": {"type": "string", "description": "Id del auto, ej. 'suv-001'"}},
            "required": ["car_id"],
        },
    },
    {
        "name": "create_reservation",
        "description": "Crea una reservación de un auto disponible para un cliente y un rango de fechas.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "car_id": {"type": "string", "description": "Id del auto a reservar"},
                "customer_name": {"type": "string", "description": "Nombre del cliente"},
                "start_date": {"type": "string", "description": "Fecha de inicio, formato YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "Fecha de fin, formato YYYY-MM-DD"},
            },
            "required": ["car_id", "customer_name", "start_date", "end_date"],
        },
    },
    {
        "name": "cancel_reservation",
        "description": "Cancela una reservación existente dado su id de reservación.",
        "inputSchema": {
            "type": "object",
            "properties": {"reservation_id": {"type": "string", "description": "Id de la reservación"}},
            "required": ["reservation_id"],
        },
    },
    {
        "name": "list_reservations",
        "description": "Lista todas las reservaciones activas, opcionalmente filtradas por cliente.",
        "inputSchema": {
            "type": "object",
            "properties": {"customer_name": {"type": "string", "description": "Filtrar por nombre de cliente"}},
            "required": [],
        },
    },
]


def _text_result(text: str, is_error: bool = False) -> dict:
    """Construye un resultado en el formato estándar de MCP para tools/call."""
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def call_tool(name: str, arguments: Dict[str, Any]) -> dict:
    """Despacha la ejecución de una tool por nombre. Retorna un resultado MCP."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return _text_result(f"Herramienta desconocida: {name}", is_error=True)
    try:
        return handler(arguments)
    except Exception as exc:  # noqa: BLE001
        return _text_result(f"Error ejecutando '{name}': {exc}", is_error=True)


def _search_cars(args: Dict[str, Any]) -> dict:
    results = CATALOG
    if "category" in args and args["category"]:
        results = [c for c in results if c["category"] == args["category"]]
    if "min_seats" in args and args["min_seats"]:
        results = [c for c in results if c["seats"] >= int(args["min_seats"])]
    if "max_price_per_day" in args and args["max_price_per_day"]:
        results = [c for c in results if c["price_per_day"] <= float(args["max_price_per_day"])]
    results = [c for c in results if c["available"]]

    if not results:
        return _text_result("No se encontraron autos disponibles con esos criterios.")

    lines = [
        f"- {c['id']}: {c['brand']} {c['model']} ({c['category']}, {c['seats']} asientos, "
        f"{c['transmission']}) — ${c['price_per_day']:.2f}/día"
        for c in results
    ]
    return _text_result("Autos disponibles:\n" + "\n".join(lines))


def _get_car_details(args: Dict[str, Any]) -> dict:
    car = next((c for c in CATALOG if c["id"] == args["car_id"]), None)
    if car is None:
        return _text_result(f"No existe un auto con id '{args['car_id']}'.", is_error=True)
    return _text_result(json.dumps(car, ensure_ascii=False, indent=2))


def _create_reservation(args: Dict[str, Any]) -> dict:
    car = next((c for c in CATALOG if c["id"] == args["car_id"]), None)
    if car is None:
        return _text_result(f"No existe un auto con id '{args['car_id']}'.", is_error=True)
    if not car["available"]:
        return _text_result(f"El auto '{args['car_id']}' no está disponible actualmente.", is_error=True)

    reservation_id = str(uuid.uuid4())[:8]
    reservation = {
        "reservation_id": reservation_id,
        "car_id": args["car_id"],
        "customer_name": args["customer_name"],
        "start_date": args["start_date"],
        "end_date": args["end_date"],
    }
    _reservations[reservation_id] = reservation
    car["available"] = False

    return _text_result(
        f"Reservación creada con éxito. Id de reservación: {reservation_id}\n"
        f"{json.dumps(reservation, ensure_ascii=False, indent=2)}"
    )


def _cancel_reservation(args: Dict[str, Any]) -> dict:
    reservation_id = args["reservation_id"]
    reservation = _reservations.pop(reservation_id, None)
    if reservation is None:
        return _text_result(f"No existe la reservación '{reservation_id}'.", is_error=True)

    car = next((c for c in CATALOG if c["id"] == reservation["car_id"]), None)
    if car is not None:
        car["available"] = True

    return _text_result(f"Reservación '{reservation_id}' cancelada correctamente.")


def _list_reservations(args: Dict[str, Any]) -> dict:
    values = list(_reservations.values())
    if "customer_name" in args and args["customer_name"]:
        values = [r for r in values if r["customer_name"].lower() == args["customer_name"].lower()]

    if not values:
        return _text_result("No hay reservaciones registradas.")

    return _text_result(json.dumps(values, ensure_ascii=False, indent=2))


_HANDLERS = {
    "search_cars": _search_cars,
    "get_car_details": _get_car_details,
    "create_reservation": _create_reservation,
    "cancel_reservation": _cancel_reservation,
    "list_reservations": _list_reservations,
}
