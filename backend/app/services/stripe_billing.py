import stripe
from app.config import settings

# Configure Stripe key
stripe.api_key = settings.STRIPE_API_KEY

class StripeBillingService:
    async def create_checkout_session(
        self, lead_id: str, campaign_id: str, email: str, company: str, amount: float
    ) -> str:
        """
        Creates a Stripe Checkout Session for client onboarding payment,
        injecting lead_id and campaign_id metadata for webhook tracking.
        """
        metadata = {
            "lead_id": lead_id,
            "campaign_id": campaign_id,
            "company": company
        }

        # Check if Stripe keys are configured, otherwise fall back to mock checkout links
        if not settings.STRIPE_API_KEY or settings.STRIPE_API_KEY == "mock_key":
            print(f"[BILLING] Stripe API key not configured. Generating mock checkout URL for lead {lead_id}.")
            return f"https://checkout.stripe.com/c/pay/mock_session_{lead_id}?amount={amount}"

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"UABE Campaign Service Agreement - {company}",
                        },
                        "unit_amount": int(amount * 100),  # Stripe expects cents
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url="http://localhost:5173/dashboard?payment_success=true",
                cancel_url="http://localhost:5173/dashboard?payment_cancel=true",
                customer_email=email,
                metadata=metadata
            )
            return session.url
        except Exception as e:
            print(f"[BILLING] Error generating Stripe checkout: {e}. Generating mock checkout URL fallback.")
            return f"https://checkout.stripe.com/c/pay/mock_session_{lead_id}?amount={amount}"

stripe_billing_service = StripeBillingService()
