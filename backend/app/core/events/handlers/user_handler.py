"""Handles user-related events (e.g. write to Firestore on user created)."""
import logging

logger = logging.getLogger(__name__)


def handle_user_created(event):
    """On user created: write to Firestore users collection (email, created_at)."""
    try:
        import firebase_admin
        from firebase_admin import firestore

        if not firebase_admin._apps:
            logger.debug("Firebase not initialized; skipping Firestore write for user_created")
            return

        db = firestore.client()
        db.collection("users").add({
            "email": event.email,
            "created_at": firestore.SERVER_TIMESTAMP,
        })
        logger.info(f"User created event: wrote to Firestore for {event.email}")
    except ImportError:
        logger.debug("firebase_admin not installed; skipping Firestore write for user_created")
    except Exception as e:
        logger.warning(f"Firestore write failed (non-fatal): {e}", exc_info=True)
