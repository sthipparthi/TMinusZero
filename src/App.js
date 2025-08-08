import React, { useEffect, useState } from "react";
import dayjs from "dayjs";
import "./SpaceBackground.css";

function App() {
  const [articles, setArticles] = useState([]);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [location, setLocation] = useState("Getting location...");

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
    };
  }, []);

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
                className="bg-white rounded-lg shadow hover:shadow-lg transition-all duration-300 overflow-hidden flex flex-col group relative"
              >
                <div className="absolute inset-0 bg-black opacity-0 group-hover:opacity-75 transition-opacity duration-300 z-10 rounded-lg"></div>
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex flex-col flex-grow relative z-20"
                >
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
                </a>
              </article>
            ))}
          </main>

          <footer className="space-footer text-white py-4 text-center">
            <p>Powered by Space News Feed · {new Date().getFullYear()}</p>
          </footer>
        </div>
      </div>
    </>
  );
}

export default App;
