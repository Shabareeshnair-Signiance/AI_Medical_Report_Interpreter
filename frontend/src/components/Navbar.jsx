function Navbar({ activePage }) {
  return (
    <nav className="bg-blue-700 px-8 py-3 flex justify-between items-center shadow-md">
      
      <span className="text-white text-lg font-bold">
        🏥 AI Medical Assistant
      </span>

      <div className="flex items-center gap-4">
        
          href="http://localhost:5000/"
          className={`px-4 py-2 rounded-md text-sm font-semibold transition-all ${
            activePage === 'patient'
              ? 'bg-white text-blue-700'
              : 'text-white hover:bg-blue-600'
          }`}
        >
          👤 Patient View
        </a>

        
          href="http://localhost:5000/doctor"
          className={`px-4 py-2 rounded-md text-sm font-semibold transition-all ${
            activePage === 'doctor'
              ? 'bg-white text-blue-700'
              : 'text-white hover:bg-blue-600'
          }`}
        >
          🩺 Doctor Dashboard
        </a>

        <span className="text-white/60 text-sm px-4 py-2 rounded-md border border-white/30">
          🔒 Doctor Login — Coming Soon
        </span>
      </div>

    </nav>
  );
}

export default Navbar;