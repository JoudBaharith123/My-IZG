"""Customer database persistence."""

from __future__ import annotations

from typing import Any

from ..db.supabase import get_supabase_client
from ..models.domain import Customer


def save_customers_to_database(customers: list[Customer]) -> int:
    """Save customers to the database.
    
    Args:
        customers: List of Customer objects to save
        
    Returns:
        Number of customers successfully saved
    """
    supabase = get_supabase_client()
    if not supabase:
        import logging
        logging.warning("Supabase not configured - customers will not be saved to database")
        return 0
    
    if not customers:
        return 0
    
    try:
        # Prepare customers for insertion
        customers_to_insert = []
        for customer in customers:
            # Convert Customer object to database record
            customer_data: dict[str, Any] = {
                "customer_id": customer.customer_id,
                "customer_name": customer.customer_name,
                "latitude": customer.latitude,
                "longitude": customer.longitude,
                "city": customer.city,
                "zone": customer.zone,
                "agent_id": customer.agent_id,
                "agent_name": customer.agent_name,
                "status": customer.status,
                "area": customer.area,
                "region": customer.region,
                "raw_data": customer.raw,  # Store raw data as JSONB
            }
            customers_to_insert.append(customer_data)
        
        if not customers_to_insert:
            return 0
        
        # Insert customers in batches (Supabase has limits)
        # Process in smaller batches to avoid timeout
        batch_size = 100
        inserted_count = 0
        updated_count = 0
        
        for i in range(0, len(customers_to_insert), batch_size):
            batch = customers_to_insert[i:i + batch_size]
            customer_ids = [c.get("customer_id") for c in batch]
            
            try:
                # Check which customers already exist (batch query)
                existing_response = supabase.table("customers").select("customer_id").in_("customer_id", customer_ids).execute()
                existing_ids = {row["customer_id"] for row in (existing_response.data or [])}
                
                # Separate into inserts and updates
                to_insert = [c for c in batch if c.get("customer_id") not in existing_ids]
                to_update = [c for c in batch if c.get("customer_id") in existing_ids]
                
                # Insert new customers in batch
                if to_insert:
                    try:
                        supabase.table("customers").insert(to_insert).execute()
                        inserted_count += len(to_insert)
                    except Exception as e:
                        import logging
                        logging.warning(f"Batch insert failed, trying individual inserts: {e}")
                        # Fall back to individual inserts
                        for customer_data in to_insert:
                            try:
                                supabase.table("customers").insert(customer_data).execute()
                                inserted_count += 1
                            except Exception:
                                continue
                
                # Update existing customers (one by one, as batch update with different values is complex)
                for customer_data in to_update:
                    try:
                        customer_id = customer_data.get("customer_id")
                        supabase.table("customers").update(customer_data).eq("customer_id", customer_id).execute()
                        updated_count += 1
                    except Exception as e:
                        import logging
                        logging.warning(f"Failed to update customer {customer_data.get('customer_id', 'unknown')}: {e}")
                        continue
                        
            except Exception as e:
                import logging
                logging.warning(f"Failed to process batch {i//batch_size + 1}: {e}")
                # Fall back to individual processing for this batch
                for customer_data in batch:
                    try:
                        customer_id = customer_data.get("customer_id")
                        existing = supabase.table("customers").select("customer_id").eq("customer_id", customer_id).limit(1).execute()
                        
                        if existing.data and len(existing.data) > 0:
                            supabase.table("customers").update(customer_data).eq("customer_id", customer_id).execute()
                            updated_count += 1
                        else:
                            supabase.table("customers").insert(customer_data).execute()
                            inserted_count += 1
                    except Exception:
                        continue
        
        import logging
        total_saved = inserted_count + updated_count
        logging.info(f"Successfully saved {total_saved} customers to database ({inserted_count} inserted, {updated_count} updated)")
        return total_saved
        
    except Exception as e:
        import logging
        logging.error(f"Failed to save customers to database: {e}")
        return 0


def clear_all_customers_from_database() -> bool:
    """Clear all customers from the database.
    
    Returns:
        True if successful, False otherwise
    """
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        # Delete all customers by selecting all and deleting
        # We need to delete in batches because Supabase/PostgREST may have limits
        batch_size = 1000
        total_deleted = 0
        
        while True:
            # Get a batch of customer IDs
            response = supabase.table("customers").select("customer_id").limit(batch_size).execute()
            
            if not response.data or len(response.data) == 0:
                break  # No more customers to delete
            
            customer_ids = [row["customer_id"] for row in response.data]
            
            # Delete this batch
            supabase.table("customers").delete().in_("customer_id", customer_ids).execute()
            total_deleted += len(customer_ids)
            
            # If we got fewer than batch_size, we're done
            if len(response.data) < batch_size:
                break
        
        import logging
        logging.info(f"Cleared {total_deleted} customers from database")
        return True
    except Exception as e:
        import logging
        logging.error(f"Failed to clear customers from database: {e}")
        return False

