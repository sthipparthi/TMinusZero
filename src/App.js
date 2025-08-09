import React, { useEffect, useState } from "react";
import dayjs from "dayjs";
import "./SpaceBackground.css";

function App() {
  const [articles, setArticles] = useState([]);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [location, setLocation] = useState("Getting location...");
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Fetch from local JSON file in /public
  const apiUrl = process.env.PUBLIC_URL + "/space_news.json";

  const fetchArticles = async () => {
    try {
      const res = await fetch(apiUrl + "?t=" + Date.now()); // Cache-busting
      const data = await res.json();
      setArticles(data || []); // Expecting an array, not { results: [] }
    } catch (error) {
      console.error("Error fetching articles:", error);
      // Demo fallback data
      setArticles([
        {
          id: 1,
          title: "SpaceX Successfully Launches Starship to Orbit",
          summary:
            "SpaceX has achieved a major milestone with the successful orbital launch of its Starship vehicle, marking a significant step forward in space exploration and Mars colonization efforts.",
          url: "https://example.com/spacex-starship",
          image_url:
            "https://images.unsplash.com/photo-1517976487492-5750f3195933?w=400&h=300&fit=crop",
          authors: [{ name: "Space Reporter" }],
          published_at: "2025-08-06T10:30:00Z",
        },
        {
          id: 2,
          title: "NASA's Artemis Mission Prepares for Moon Landing",
          summary:
            "NASA continues preparations for the upcoming Artemis mission that will return humans to the Moon for the first time since the Apollo program ended in 1972.",
          url: "https://example.com/artemis-mission",
          image_url:
            "https://images.unsplash.com/photo-1446776877081-d282a0f896e2?w=400&h=300&fit=crop",
          authors: [{ name: "NASA News" }],
          published_at: "2025-08-05T14:20:00Z",
        },
        {
          id: 3,
          title: "Private Space Station Development Accelerates",
          summary:
            "Multiple companies are racing to develop commercial space stations as the International Space Station approaches the end of its operational life in the coming decade.",
          url: "https://example.com/private-space-station",
          image_url:
            "https://images.unsplash.com/photo-1614728894747-a83421e2b9c9?w=400&h=300&fit=crop",
          authors: [{ name: "Commercial Space News" }],
          published_at: "2025-08-04T09:15:00Z",
        },
      ]);
    }
  };

  const getLocation = async () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          try {
            const { latitude, longitude } = position.coords;
            const response = await fetch(
              `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=en`
            );
            const data = await response.json();
            setLocation(
              `${data.city || data.locality || "Unknown"}, ${
                data.countryCode || ""
              }`
            );
          } catch (error) {
            console.error("Error getting location name:", error);
            setLocation("Location unavailable");
          }
        },
        (error) => {
          console.error("Error getting location:", error);
          setLocation("Location unavailable");
        }
      );
    } else {
      setLocation("Geolocation not supported");
    }
  };

  useEffect(() => {
    fetchArticles();
    getLocation();

    const articleInterval = setInterval(fetchArticles, 60 * 60 * 1000); // Hourly
    const clockInterval = setInterval(
      () => setCurrentTime(new Date()),
      1000
    ); // Every second

    return () => {
      clearInterval(articleInterval);
      clearInterval(clockInterval);
      // Cleanup: restore scrolling if component unmounts
      document.body.style.overflow = 'unset';
    };
  }, []);

  const openModal = (article) => {
    setSelectedArticle(article);
    setIsModalOpen(true);
    // Prevent background scrolling
    document.body.style.overflow = 'hidden';
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedArticle(null);
    // Restore background scrolling
    document.body.style.overflow = 'unset';
  };

  const handleModalBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      closeModal();
    }
  };

  return (
    <>
      {/* Fixed Space Background */}
      <div className="space-background"></div>

      {/* Main Content Overlay */}
      <div className="min-h-screen flex flex-col">
        <div className="space-overlay max-w-7xl mx-auto min-h-screen flex flex-col">
          <header className="space-header text-white py-6 shadow">
            <div className="px-4 flex justify-between items-center">
              <h1 className="text-3xl font-bold">🚀 Space Launch News</h1>
              <div className="text-right">
                <div className="text-lg font-semibold">
                  {currentTime.toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: true,
                  })}
                </div>
                <div className="text-sm opacity-90">📍 {location}</div>
              </div>
            </div>
          </header>

          <main className="flex-grow p-4 grid gap-3 grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {articles.map((article) => (
              <article
                key={article.id}
                className="bg-white rounded-lg shadow hover:shadow-lg transition-all duration-300 overflow-hidden flex flex-col group relative cursor-pointer"
                onClick={() => openModal(article)}
              >
                <div className="absolute inset-0 bg-black opacity-0 group-hover:opacity-75 transition-opacity duration-300 z-10 rounded-lg"></div>
                <div className="flex flex-col flex-grow relative z-20">
                  <img
                    src={article.image_url}
                    alt={article.title}
                    className="w-full h-48 object-cover"
                  />
                  <div className="p-4 flex flex-col flex-grow">
                    <h2 className="font-semibold text-lg mb-2 flex-grow group-hover:text-white transition-colors duration-300">
                      {article.title}
                    </h2>
                    <p className="text-gray-700 text-sm mb-3 line-clamp-3 group-hover:text-gray-200 transition-colors duration-300">
                      {article.summary}
                    </p>
                    <p className="text-gray-500 text-xs group-hover:text-gray-300 transition-colors duration-300">
                      {article.news_site || article.authors?.[0]?.name} ·{" "}
                      {dayjs(article.published_at).format("MMM D, YYYY")}
                    </p>
                  </div>
                </div>
              </article>
            ))}
          </main>

          <footer className="space-footer text-white py-4 text-center">
            <p>Powered by Space News Feed · {new Date().getFullYear()}</p>
          </footer>
        </div>
      </div>

      {/* Modal */}
      {isModalOpen && selectedArticle && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={handleModalBackdropClick}
        >
          <div className="modal-container modal-space-bg rounded-lg max-w-4xl w-full max-h-[90vh] relative overflow-hidden">
            {/* Close Button */}
            <button 
              onClick={closeModal}
              className="absolute top-4 right-4 text-gray-300 hover:text-white text-2xl font-bold z-10 bg-black bg-opacity-50 hover:bg-opacity-70 rounded-full w-8 h-8 flex items-center justify-center shadow-lg transition-all duration-200"
            >
              ×
            </button>
            
            {/* Modal Content */}
            <div className="p-6 overflow-y-auto max-h-[90vh] text-white">
              {/* Header Image */}
              <img
                src={selectedArticle.image_url}
                alt={selectedArticle.title}
                className="w-full h-64 object-cover rounded-lg mb-6"
              />
              
              {/* Article Info */}
              <div className="mb-4">
                <div className="flex items-center gap-2 text-sm text-gray-300 mb-2">
                  <span className="font-medium text-gray-200">{selectedArticle.news_site || selectedArticle.authors?.[0]?.name}</span>
                  <span>·</span>
                  <span>{dayjs(selectedArticle.published_at).format("MMMM D, YYYY at h:mm A")}</span>
                </div>
                
                {/* Authors */}
                {selectedArticle.authors && selectedArticle.authors.length > 0 && (
                  <div className="text-sm text-gray-300 mb-4">
                    By: {selectedArticle.authors.map(author => author.name).join(", ")}
                  </div>
                )}
              </div>
              
              {/* Title */}
              <h1 className="text-3xl font-bold text-white mb-6">
                {selectedArticle.title}
              </h1>
              
              {/* Detailed News Content */}
              <div className="prose prose-lg max-w-none mb-6">
                {selectedArticle.detailed_news && selectedArticle.detailed_news.trim() !== "" ? (
                  <div className="text-gray-200 leading-relaxed whitespace-pre-wrap">
                    {selectedArticle.detailed_news}
                  </div>
                ) : selectedArticle.summary ? (
                  <div className="text-gray-200 leading-relaxed">
                    {selectedArticle.summary}
                  </div>
                ) : (
                  <div className="text-gray-300 italic">
                    <p>Content is being processed. Please check back later for the complete article summary.</p>
                  </div>
                )}
              </div>
              
              {/* Action Buttons */}
              <div className="flex gap-4 pt-4 border-t border-gray-600">
                <a
                  href={selectedArticle.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors duration-200 flex items-center gap-2"
                >
                  Read Original Article
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
                <button
                  onClick={closeModal}
                  className="bg-gray-700 text-gray-200 px-6 py-2 rounded-lg hover:bg-gray-600 transition-colors duration-200"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default App;
