"""Supabase client for Python backend."""

from functools import lru_cache
from supabase import create_client, Client
from ..config import settings


@lru_cache()
def get_supabase_client() -> Client | None:
    """Get cached Supabase client instance."""
    if not settings.supabase_url or not settings.supabase_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_key)


# Convenience alias
supabase = get_supabase_client()


# Example usage patterns:
#
# from .db.supabase import supabase
#
# # Insert
# result = supabase.table('customers').insert({
#     'customer_id': '123',
#     'customer_name': 'Test',
#     'latitude': 24.7136,
#     'longitude': 46.6753,
# }).execute()
#
# # Select with filters
# result = supabase.table('customers') \
#     .select('*') \
#     .eq('city', 'Riyadh') \
#     .limit(100) \
#     .execute()
#
# # Update
# result = supabase.table('customers') \
#     .update({'zone': 'Zone A'}) \
#     .eq('customer_id', '123') \
#     .execute()
#
# # Delete
# result = supabase.table('customers') \
#     .delete() \
#     .eq('customer_id', '123') \
#     .execute()
#
# # RPC (stored procedures)
# result = supabase.rpc('get_customers_in_radius', {
#     'lat': 24.7136,
#     'lng': 46.6753,
#     'radius_km': 10
# }).execute()
