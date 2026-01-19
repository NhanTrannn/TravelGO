import { create } from 'zustand';

interface ListingModalStore {
  isOpen: boolean;
  onOpen: () => void;
  onClose: () => void;
}

const useListingModal = create<ListingModalStore>((set) => ({
  isOpen: false,
  onOpen: () => set({ isOpen: true }),
  onClose: () => set({ isOpen: false }),
}));

export default useListingModal;
