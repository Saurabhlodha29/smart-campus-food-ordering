import { useState } from "react";
import toast from "react-hot-toast";
import { initiatePayment, verifyPayment } from "../api/payments";
import { apiErrorMessage } from "../api/client";

const loadRazorpay = () =>
  new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });

export function useRazorpay() {
  const [loading, setLoading] = useState(false);

  const pay = async (orderId, options = {}) => {
    setLoading(true);
    try {
      if (!(await loadRazorpay())) throw new Error("Razorpay checkout could not be loaded");
      const initiation = await initiatePayment(orderId);
      await new Promise((resolve, reject) => {
        const razorpay = new window.Razorpay({
          key: import.meta.env.VITE_RAZORPAY_KEY_ID || initiation.keyId,
          amount: Math.round(initiation.amount * 100),
          currency: initiation.currency || "INR",
          order_id: initiation.razorpayOrderId,
          name: "Smart Campus Food",
          ...options,
          handler: async (response) => {
            try {
              const result = await verifyPayment({
                razorpayOrderId: response.razorpay_order_id,
                razorpayPaymentId: response.razorpay_payment_id,
                razorpaySignature: response.razorpay_signature,
              });
              resolve(result);
            } catch (error) { reject(error); }
          },
          modal: { ondismiss: () => reject(new Error("Payment cancelled")) },
        });
        razorpay.open();
      });
      toast.success("Payment verified");
      return true;
    } catch (error) {
      toast.error(apiErrorMessage(error));
      return false;
    } finally { setLoading(false); }
  };

  return { pay, loading };
}
