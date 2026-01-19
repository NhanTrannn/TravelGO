"use client"

import { useState } from "react"
import { useForm, SubmitHandler } from "react-hook-form"
import { signIn } from "next-auth/react"
import { toast } from "react-hot-toast"
import { useRouter } from "next/navigation"
import Modal from "@/components/ui/Modal"
import useLoginModal from "@/hooks/useLoginModal"
import useRegisterModal from "@/hooks/useRegisterModal"
import { Input } from "@/components/ui/Input"
import { Button } from "@/components/ui/Button"

interface LoginFormData {
  email: string
  password: string
}

const LoginModal = () => {
  const router = useRouter()
  const loginModal = useLoginModal()
  const registerModal = useRegisterModal()
  const [isLoading, setIsLoading] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<LoginFormData>()

  const onSubmit: SubmitHandler<LoginFormData> = async (data) => {
    setIsLoading(true)

    try {
      const result = await signIn('credentials', {
        ...data,
        redirect: false,
      })

      if (result?.error) {
        toast.error(result.error)
      } else {
        toast.success('Đăng nhập thành công!')
        loginModal.onClose()
        reset()
        router.refresh()
      }
    } catch {
      toast.error('Đã xảy ra lỗi!')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSwitchToRegister = () => {
    loginModal.onClose()
    setTimeout(() => {
      registerModal.onOpen()
    }, 300)
  }

  return (
    <Modal
      isOpen={loginModal.isOpen}
      onClose={loginModal.onClose}
      title="Đăng nhập"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Email/Username Field */}
        <div>
          <label htmlFor="login-email" className="block text-sm font-medium text-gray-700 mb-1">
            Email hoặc Username
          </label>
          <Input
            id="login-email"
            type="text"
            disabled={isLoading}
            {...register('email', {
              required: 'Vui lòng nhập email hoặc username',
            })}
            placeholder="email@example.com hoặc username"
          />
          {errors.email && (
            <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
          )}
        </div>

        {/* Password Field */}
        <div>
          <label htmlFor="login-password" className="block text-sm font-medium text-gray-700 mb-1">
            Mật khẩu
          </label>
          <Input
            id="login-password"
            type="password"
            disabled={isLoading}
            {...register('password', {
              required: 'Vui lòng nhập mật khẩu',
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
          {isLoading ? 'Đang đăng nhập...' : 'Đăng nhập'}
        </Button>

        {/* Switch to Register */}
        <div className="text-center text-sm text-gray-600">
          Chưa có tài khoản?{' '}
          <button
            type="button"
            onClick={handleSwitchToRegister}
            className="text-blue-600 hover:underline font-medium"
            disabled={isLoading}
          >
            Đăng ký ngay
          </button>
        </div>
      </form>
    </Modal>
  )
}

export default LoginModal
