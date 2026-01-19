"use client"

import useListingModal from '@/hooks/useListingModal';
import useLoginModal from '@/hooks/useLoginModal';
import useRegisterModal from '@/hooks/useRegisterModal';
import { Home, LogOut, MapPin, Menu, Phone, PlusCircle, User, X } from 'lucide-react';
import { signOut, useSession } from 'next-auth/react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

const Navbar = () => {
  const { data: session } = useSession();
  const pathname = usePathname();

  // Modals
  const loginModal = useLoginModal();
  const registerModal = useRegisterModal();
  const listingModal = useListingModal();

  // UI States
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Close user menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Navigation Links Data
  const navLinks = [
    { href: '/', label: 'Trang chủ', icon: Home },
    { href: '/destinations', label: 'Điểm đến', icon: MapPin },
    { href: '/contact', label: 'Liên hệ', icon: Phone },
  ];

  return (
    <nav className="bg-white/80 backdrop-blur-md border-b border-gray-100 fixed top-0 left-0 w-full z-50 transition-all">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">

          {/* --- LOGO --- */}
          <div className="shrink-0 flex items-center gap-2">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-lg shadow-blue-200 shadow-lg group-hover:scale-105 transition-transform">
                T
              </div>
              <span className="text-xl font-bold bg-clip-text text-transparent bg-linear-to-r from-blue-600 to-blue-400">
                TravelGO
              </span>
            </Link>
          </div>

          {/* --- DESKTOP NAVIGATION --- */}
          <div className="hidden md:flex space-x-8">
            {navLinks.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`inline-flex items-center px-1 pt-1 text-sm font-medium transition-colors border-b-2 ${
                    isActive
                      ? 'text-blue-600 border-blue-600'
                      : 'text-gray-500 border-transparent hover:text-blue-600 hover:border-blue-200'
                  }`}
                >
                  {link.label}
                </Link>
              )
            })}
          </div>

          {/* --- RIGHT ACTIONS (AUTH) --- */}
          <div className="hidden md:flex items-center space-x-4">
            {session?.user ? (
              <div className="relative" ref={userMenuRef}>
                {/* User Avatar Button */}
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center gap-2 hover:bg-gray-50 p-1.5 rounded-full border border-gray-200 transition-all focus:ring-2 focus:ring-blue-100"
                >
                  <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 overflow-hidden">
                    {session.user.image ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={session.user.image} alt="User" className="w-full h-full object-cover" />
                    ) : (
                      <User size={18} />
                    )}
                  </div>
                  <span className="text-sm font-medium text-gray-700 max-w-[100px] truncate pr-1">
                    {session.user.name || "User"}
                  </span>
                </button>

                {/* User Dropdown Menu */}
                {isUserMenuOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-gray-100 py-2 animate-in fade-in zoom-in duration-200 origin-top-right">
                    <div className="px-4 py-2 border-b border-gray-50">
                      <p className="text-xs text-gray-500">Đang đăng nhập với</p>
                      <p className="text-sm font-semibold text-gray-900 truncate">{session.user.email}</p>
                    </div>

                    <button
                      onClick={() => {
                        listingModal.onOpen();
                        setIsUserMenuOpen(false);
                      }}
                      className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-blue-50 hover:text-blue-600 flex items-center gap-2"
                    >
                      <PlusCircle size={16} /> Tạo Listing mới
                    </button>

                    <div className="border-t border-gray-50 my-1"></div>

                    <button
                      onClick={() => signOut()}
                      className="w-full text-left px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                    >
                      <LogOut size={16} /> Đăng xuất
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <>
                <button
                  onClick={loginModal.onOpen}
                  className="text-gray-600 hover:text-blue-600 font-medium text-sm transition-colors"
                >
                  Đăng nhập
                </button>
                <button
                  onClick={registerModal.onOpen}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-full text-sm font-medium shadow-md hover:shadow-lg transition-all transform hover:-translate-y-0.5"
                >
                  Đăng ký ngay
                </button>
              </>
            )}
          </div>

          {/* --- MOBILE MENU BUTTON --- */}
          <div className="flex items-center md:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-500 hover:text-blue-600 hover:bg-gray-100 focus:outline-none"
            >
              {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </div>

      {/* --- MOBILE MENU DROPDOWN --- */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-gray-100 bg-white shadow-lg">
          <div className="pt-2 pb-3 space-y-1 px-4">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setIsMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-3 py-3 rounded-lg text-base font-medium ${
                  pathname === link.href
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-blue-600'
                }`}
              >
                <link.icon size={18} />
                {link.label}
              </Link>
            ))}
          </div>

          <div className="pt-4 pb-4 border-t border-gray-100 px-4">
            {session?.user ? (
              <div className="space-y-3">
                <div className="flex items-center gap-3 px-3">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                    {session.user.image ? <img src={session.user.image} className="rounded-full" alt="" /> : <User />}
                  </div>
                  <div>
                    <div className="font-medium text-gray-800">{session.user.name}</div>
                    <div className="text-sm text-gray-500">{session.user.email}</div>
                  </div>
                </div>
                <button
                  onClick={() => { listingModal.onOpen(); setIsMobileMenuOpen(false); }}
                  className="w-full mt-2 flex items-center justify-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg font-medium"
                >
                  <PlusCircle size={18} /> Tạo Listing
                </button>
                <button
                  onClick={() => signOut()}
                  className="w-full flex items-center justify-center gap-2 border border-gray-200 text-gray-600 px-4 py-2 rounded-lg font-medium hover:bg-gray-50"
                >
                  <LogOut size={18} /> Đăng xuất
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => { loginModal.onOpen(); setIsMobileMenuOpen(false); }}
                  className="w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-lg text-base font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  Đăng nhập
                </button>
                <button
                  onClick={() => { registerModal.onOpen(); setIsMobileMenuOpen(false); }}
                  className="w-full flex items-center justify-center px-4 py-2 border border-transparent rounded-lg text-base font-medium text-white bg-blue-600 hover:bg-blue-700"
                >
                  Đăng ký
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
