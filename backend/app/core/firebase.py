"""Firebase Admin SDK initialization for Firestore (e.g. user signup sync)."""
import os
import logging

from ..config import settings

logger = logging.getLogger(__name__)


def init_firebase():
    """Initialize Firebase Admin SDK when GOOGLE_APPLICATION_CREDENTIALS is set. Safe to call if not configured."""
    try:
        import firebase_admin
        if firebase_admin._apps:
            return
        path = getattr(settings, "google_application_credentials", None)
        if path and os.path.isfile(path):
            cred = firebase_admin.credentials.Certificate(path)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized for Firestore")
        else:
            logger.debug("GOOGLE_APPLICATION_CREDENTIALS not set or file missing; Firebase disabled")
    except ImportError:
        logger.debug("firebase_admin not installed; Firebase disabled")
    except Exception as e:
        logger.warning(f"Firebase init failed (non-fatal): {e}", exc_info=True)
