"use client"

import LoginModal from "@/components/features/auth/LoginModal"
import RegisterModal from "@/components/features/auth/RegisterModal"

const ModalProvider = () => {
  return (
    <>
      <LoginModal />
      <RegisterModal />
    </>
  )
}

export default ModalProvider
