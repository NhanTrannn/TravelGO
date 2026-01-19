import * as React from "react"
import { cn } from "@/lib/utils"
import { FieldErrors, UseFormRegister } from "react-hook-form"

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  id: string
  label?: string
  register?: UseFormRegister<Record<string, unknown>>
  errors?: FieldErrors
  required?: boolean
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ id, label, register, errors, required, className, type = "text", ...props }, ref) => {
    const inputProps = register ? register(id, { required }) : {};
    return (
      <div className="w-full">
        {label && (
          <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
            {label}
          </label>
        )}
        <input
          id={id}
          type={type}
          className={cn(
            "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            errors && errors[id] ? "border-red-500" : "",
            className
          )}
          ref={ref}
          {...inputProps}
          {...props}
        />
        {errors && errors[id] && (
          <span className="text-xs text-red-500">{errors[id]?.message as string}</span>
        )}
      </div>
    )
  }
)
Input.displayName = "Input"

export { Input }