"use client"

import { useState } from "react"
import { useForm, SubmitHandler } from "react-hook-form"
import axios from "axios"
import { toast } from "react-hot-toast"
import Modal from "@/components/ui/Modal"
import useRegisterModal from "@/hooks/useRegisterModal"
import useLoginModal from "@/hooks/useLoginModal"
import { Input } from "@/components/ui/Input"
import { Button } from "@/components/ui/Button"

interface RegisterFormData {
  name: string
  email: string
  password: string
}

const RegisterModal = () => {
  const registerModal = useRegisterModal()
  const loginModal = useLoginModal()
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<RegisterFormData>()

  const onSubmit: SubmitHandler<RegisterFormData> = async (data) => {
    setIsLoading(true)

    try {
      await axios.post('/api/register', data)
      
      toast.success('Đăng ký thành công! Vui lòng đăng nhập.')
      
      registerModal.onClose()
      reset()
      
      // Mở modal đăng nhập sau khi đăng ký thành công
      setTimeout(() => {
        loginModal.onOpen()
      }, 300)
      
    } catch (error) {
      if (axios.isAxiosError(error)) {
        toast.error(error.response?.data || 'Đã xảy ra lỗi!')
      } else {
        toast.error('Đã xảy ra lỗi!')
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleSwitchToLogin = () => {
    registerModal.onClose()
    setTimeout(() => {
      loginModal.onOpen()
    }, 300)
  }

  return (
    <Modal
      isOpen={registerModal.isOpen}
      onClose={registerModal.onClose}
      title="Đăng ký tài khoản"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Name Field */}
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
            Họ và tên
          </label>
          <Input
            id="name"
            type="text"
            disabled={isLoading}
            {...register('name', {
              required: 'Vui lòng nhập họ tên',
              minLength: {
                value: 2,
                message: 'Họ tên phải có ít nhất 2 ký tự',
              },
            })}
            placeholder="Nguyễn Văn A"
          />
          {errors.name && (
            <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
          )}
        </div>

        {/* Email Field */}
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
            Email
          </label>
          <Input
            id="email"
            type="email"
            disabled={isLoading}
            {...register('email', {
              required: 'Vui lòng nhập email',
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: 'Email không hợp lệ',
              },
            })}
            placeholder="example@email.com"
          />
          {errors.email && (
            <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
          )}
        </div>

        {/* Password Field */}
        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
            Mật khẩu
          </label>
          <Input
            id="password"
            type="password"
            disabled={isLoading}
            {...register('password', {
              required: 'Vui lòng nhập mật khẩu',
              minLength: {
                value: 6,
                message: 'Mật khẩu phải có ít nhất 6 ký tự',
              },
            })}
            placeholder="••••••••"
          />
          {errors.password && (
            <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
          )}
        </div>

        {/* Submit Button */}
        <Button
          type="submit"
          disabled={isLoading}
          className="w-full"
        >
          {isLoading ? 'Đang xử lý...' : 'Đăng ký'}
        </Button>

        {/* Switch to Login */}
        <div className="text-center text-sm text-gray-600">
          Đã có tài khoản?{' '}
          <button
            type="button"
            onClick={handleSwitchToLogin}
            className="text-blue-600 hover:underline font-medium"
            disabled={isLoading}
          >
            Đăng nhập ngay
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default RegisterModal
