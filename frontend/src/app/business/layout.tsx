/**
 * Business Dashboard Layout
 * Có B2B Navbar, không có Footer
 */
import B2BNavbar from "@/components/shared/B2BNavbar";

export default function BusinessLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gray-50">
      <B2BNavbar />
      {children}
    </div>
  );
}
