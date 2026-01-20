"""
Detector Alerting Utilities

This module handles the logic for triggering detector-based alerts.
Called after a query result is processed to determine if an alert should be sent.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from .. import models

logger = logging.getLogger(__name__)


def should_trigger_alert(
    detector_id: str,
    result_label: str,
    confidence: float,
    db: Session
) -> bool:
    """
    Check if alert should be triggered based on detector alert configuration.

    Args:
        detector_id: UUID of the detector
        result_label: Detection result label (e.g., "YES", "Person", "Defect")
        confidence: Detection confidence score (0-1)
        db: Database session

    Returns:
        True if alert should be triggered, False otherwise
    """
    # Get alert config for this detector
    config = db.query(models.DetectorAlertConfig).filter(
        models.DetectorAlertConfig.detector_id == detector_id
    ).first()

    if not config or not config.enabled:
        return False

    # Check condition type
    if config.condition_type == "ALWAYS":
        return True

    elif config.condition_type == "LABEL_MATCH":
        # Alert if label matches the configured value
        if config.condition_value:
            return result_label.upper() == config.condition_value.upper()
        return False

    elif config.condition_type == "CONFIDENCE_THRESHOLD":
        # Alert if confidence exceeds threshold
        if config.condition_value:
            try:
                threshold = float(config.condition_value)
                return confidence >= threshold
            except ValueError:
                logger.error(f"Invalid confidence threshold: {config.condition_value}")
                return False
        return False

    # Unknown condition type
    logger.warning(f"Unknown condition type: {config.condition_type}")
    return False


def check_cooldown(
    detector_id: str,
    cooldown_minutes: int,
    db: Session
) -> bool:
    """
    Check if cooldown period has passed since last alert.

    Args:
        detector_id: UUID of the detector
        cooldown_minutes: Cooldown period in minutes
        db: Database session

    Returns:
        True if cooldown has passed (can send alert), False otherwise
    """
    cutoff_time = datetime.utcnow() - timedelta(minutes=cooldown_minutes)

    # Get most recent alert for this detector
    last_alert = db.query(models.DetectorAlert).filter(
        models.DetectorAlert.detector_id == detector_id,
        models.DetectorAlert.created_at > cutoff_time
    ).order_by(models.DetectorAlert.created_at.desc()).first()

    # If no recent alert, cooldown has passed
    return last_alert is None


def create_alert_message(
    detector_name: str,
    result_label: str,
    confidence: float,
    camera_name: Optional[str],
    custom_message: Optional[str]
) -> str:
    """
    Create alert message from template or default format.

    Args:
        detector_name: Name of the detector
        result_label: Detection result label
        confidence: Detection confidence score
        camera_name: Name of the camera (if applicable)
        custom_message: Custom message template (optional)

    Returns:
        Formatted alert message
    """
    if custom_message:
        # Replace placeholders in custom message
        message = custom_message
        message = message.replace("{detector_name}", detector_name)
        message = message.replace("{label}", result_label)
        message = message.replace("{confidence}", f"{confidence:.2%}")
        if camera_name:
            message = message.replace("{camera_name}", camera_name)
        return message

    # Default message format
    base_message = f"Alert: {detector_name} detected '{result_label}' (confidence: {confidence:.2%})"

    if camera_name:
        base_message += f" on camera '{camera_name}'"

    return base_message


def send_alert_emails(
    recipients: list[str],
    subject: str,
    message: str,
    image_url: Optional[str] = None
):
    """
    Send alert emails to recipients.

    Args:
        recipients: List of email addresses
        subject: Email subject
        message: Email body
        image_url: Optional URL to detection image
    """
    if not recipients:
        logger.warning("No recipients configured for alert")
        return

    # TODO: Integrate with actual email sending (SendGrid, alerts.py, etc.)
    logger.info(f"Would send detector alert email to {recipients}: {subject}")
    logger.info(f"Message: {message}")

    # For now, just log that we would send emails
    # In production, integrate with SendGrid or existing alert system


def trigger_detector_alert(
    detector_id: str,
    query_id: str,
    result_label: str,
    confidence: float,
    camera_name: Optional[str],
    image_blob_path: Optional[str],
    db: Session
) -> Optional[str]:
    """
    Main function to trigger a detector alert.

    This function:
    1. Checks if alert should be triggered based on configuration
    2. Checks cooldown period
    3. Creates alert record
    4. Sends email notifications (async)

    Args:
        detector_id: UUID of the detector
        query_id: UUID of the query that triggered the alert
        result_label: Detection result label
        confidence: Detection confidence score
        camera_name: Name of the camera (if applicable)
        image_blob_path: Path to detection image in blob storage
        db: Database session

    Returns:
        Alert ID if alert was created, None otherwise
    """
    # Get detector
    detector = db.query(models.Detector).filter(
        models.Detector.id == detector_id
    ).first()

    if not detector:
        logger.error(f"Detector not found: {detector_id}")
        return None

    # Get alert config
    config = db.query(models.DetectorAlertConfig).filter(
        models.DetectorAlertConfig.detector_id == detector_id
    ).first()

    if not config or not config.enabled:
        # No alert config or alerts disabled
        return None

    # Check if alert should be triggered
    if not should_trigger_alert(detector_id, result_label, confidence, db):
        logger.debug(f"Alert conditions not met for detector {detector.name}")
        return None

    # Check cooldown period
    if not check_cooldown(detector_id, config.cooldown_minutes, db):
        logger.info(f"Cooldown period active for detector {detector.name}, skipping alert")
        return None

    # Create alert message
    message = create_alert_message(
        detector_name=detector.name,
        result_label=result_label,
        confidence=confidence,
        camera_name=camera_name,
        custom_message=config.custom_message
    )

    # Create alert record
    alert = models.DetectorAlert(
        detector_id=detector_id,
        query_id=query_id,
        alert_type="DETECTION",
        severity=config.severity,
        message=message,
        detection_label=result_label,
        detection_confidence=confidence,
        camera_name=camera_name,
        image_blob_path=image_blob_path,
        sent_to=config.alert_emails,
        email_sent=False
    )

    db.add(alert)
    db.commit()
    db.refresh(alert)

    logger.info(f"Created alert {alert.id} for detector {detector.name}")

    # Send email notifications
    if config.alert_emails:
        try:
            subject = f"[{config.severity.upper()}] {detector.name} Alert"

            send_alert_emails(
                recipients=config.alert_emails,
                subject=subject,
                message=message,
                image_url=image_blob_path
            )

            alert.email_sent = True
            alert.email_sent_at = datetime.utcnow()
            db.commit()

        except Exception as e:
            logger.error(f"Failed to send alert emails: {e}")

    return str(alert.id)
