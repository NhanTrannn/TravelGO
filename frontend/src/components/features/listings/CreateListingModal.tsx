"use client"

import React, { useState } from "react"
import { useForm, SubmitHandler, FieldValues } from "react-hook-form"
import axios from "axios"
import toast from "react-hot-toast"
import { useRouter } from "next/navigation"

import useListingModal from "@/hooks/useListingModal"
import Modal from "@/components/ui/Modal"
import { Input } from "@/components/ui/Input"
import { Button } from "@/components/ui/Button"
import ImageUpload from "@/components/ui/ImageUpload"

const CreateListingModal = () => {
  const router = useRouter()
  const listingModal = useListingModal()
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
    reset,
  } = useForm<FieldValues>({
    defaultValues: {
      title: "",
      description: "",
      imageSrc: "",
      location: "",
      price: "",
    },
  })

  // Không memo hóa imageSrc, chỉ dùng trực tiếp
  const imageSrc = watch("imageSrc")

  const setCustomValue = (id: string, value: unknown) => {
    setValue(id, value, {
      shouldDirty: true,
      shouldTouch: true,
      shouldValidate: true,
    })
  }

  const onSubmit: SubmitHandler<FieldValues> = (data) => {
    setIsLoading(true)
    const loadingToast = toast.loading("Đang tạo listing...")

    axios
      .post("/api/listings", data)
      .then(() => {
        toast.success("Tạo listing thành công!")
        router.refresh()
        reset()
        listingModal.onClose()
      })
      .catch((error) => {
        toast.error(error.response?.data || "Đã xảy ra lỗi")
      })
      .finally(() => {
        setIsLoading(false)
        toast.dismiss(loadingToast)
      })
  }

  const bodyContent = (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <ImageUpload
        value={imageSrc}
        onChange={(value) => setCustomValue("imageSrc", value)}
      />
      {errors.imageSrc && (
         <span className="text-xs text-red-500">Ảnh là bắt buộc</span>
      )}

      <Input
        id="title"
        label="Tiêu đề (Ví dụ: Khách sạn Mường Thanh)"
        disabled={isLoading}
        register={register}
        errors={errors}
        required
      />
      <Input
        id="description"
        label="Mô tả"
        disabled={isLoading}
        register={register}
        errors={errors}
        required
      />
      <Input
        id="location"
        label="Vị trí (Ví dụ: Đà Lạt, Việt Nam)"
        disabled={isLoading}
        register={register}
        errors={errors}
        required
      />
      <Input
        id="price"
        label="Giá (VND / đêm)"
        type="number"
        disabled={isLoading}
        register={register}
        errors={errors}
        required
      />
      <div className="mt-4">
        <Button disabled={isLoading} type="submit" className="w-full">
          {isLoading ? "Đang tạo..." : "Tạo Listing"}
        </Button>
      </div>
    </form>
  )

  return (
    <Modal
      isOpen={listingModal.isOpen}
      onClose={listingModal.onClose}
      title="Tạo Listing mới"
    >
      {bodyContent}
    </Modal>
  )
}

export default CreateListingModal
