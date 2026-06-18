import { create } from "zustand";

export const useCartStore = create((set, get) => ({
  items: [],
  outletId: null,
  selectedSlotId: null,
  paymentMethod: "ONLINE",

  addItem: (item, outletId) => {
    const { items, outletId: currentOutlet } = get();
    if (currentOutlet && currentOutlet !== outletId) {
      set({ items: [{ item, quantity: 1 }], outletId });
      return;
    }
    const existing = items.find((i) => i.item.id === item.id);
    if (existing) {
      set({ items: items.map((i) => i.item.id === item.id ? { ...i, quantity: i.quantity + 1 } : i) });
    } else {
      set({ items: [...items, { item, quantity: 1 }], outletId });
    }
  },

  removeItem: (itemId) => {
    const { items } = get();
    const existing = items.find((i) => i.item.id === itemId);
    if (!existing) return;
    if (existing.quantity === 1) {
      const newItems = items.filter((i) => i.item.id !== itemId);
      set({ items: newItems, outletId: newItems.length === 0 ? null : get().outletId });
    } else {
      set({ items: items.map((i) => i.item.id === itemId ? { ...i, quantity: i.quantity - 1 } : i) });
    }
  },

  clearCart: () => set({ items: [], outletId: null, selectedSlotId: null }),
  setSlot: (slotId) => set({ selectedSlotId: slotId }),
  setPaymentMethod: (method) => set({ paymentMethod: method }),
  total: () => get().items.reduce((sum, i) => sum + i.item.price * i.quantity, 0),
  itemCount: () => get().items.reduce((sum, i) => sum + i.quantity, 0),
}));
