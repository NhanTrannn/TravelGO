const Footer = () => {
  return (
    <footer className="bg-gray-50 border-t border-gray-200">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-between items-center">
          <p className="text-center text-sm text-gray-500">
            &copy; {new Date().getFullYear()} TravelGO. Phát triển bởi [Tên của bạn].
          </p>
          <div className="flex space-x-6">
            {/* Bạn có thể thêm các link mạng xã hội ở đây */}
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
