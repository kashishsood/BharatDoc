import { Link, useLocation } from 'react-router-dom';

export default function Navbar() {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="fixed top-0 left-0 right-0 bg-slate-900 border-b border-slate-700 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center">
            <Link to="/" className="text-2xl font-bold text-blue-400 hover:text-blue-300 transition-colors">
              BharatDoc
            </Link>
          </div>

          <div className="flex items-center space-x-8">
            <Link
              to="/"
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/')
                  ? 'text-white bg-slate-800 border-b-2 border-blue-400'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              Dashboard
            </Link>
            <Link
              to="/extract"
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                isActive('/extract')
                  ? 'text-white bg-slate-800 border-b-2 border-blue-400'
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              Extract
            </Link>
          </div>

          <div className="text-xs text-slate-400">
            Powered by LoRA + Bedrock
          </div>
        </div>
      </div>
    </nav>
  );
}
