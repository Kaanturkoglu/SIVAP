import React, { useState } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  useNavigate,
} from "react-router-dom";
import HomeScreen from "./screens/HomeScreen/HomeScreen.tsx";
import DataShowScreen from "./screens/HomeScreen/DataShowScreen.tsx";
import Sider from "./components/Sider";
import ChurnersProfileScreen from "./screens/HomeScreen/ChurnersProfileScreen.tsx";
import BaseCustomer from "./screens/HomeScreen/BaseCustomer.tsx";
import CallListScreen from "./screens/HomeScreen/CallListScreen.tsx";

// Wrapper component that uses the useNavigate hook

const AppRoutes = ({
  results,
  handleProcessComplete,
}: {
  results: { name: string }[];
  handleProcessComplete: (resultName: string) => void;
}) => (
  <Routes>
    <Route
      path="/"
      element={
        <HomeScreen
          results={results}
          onProcessComplete={handleProcessComplete}
        />
      }
    />
    <Route path="/data-show" element={<DataShowScreen results={results} />} />
    <Route
      path="/churners-profile"
      element={
        <ChurnersProfileScreen
          results={results}
          onProcessComplete={function (resultName: string): void {
            throw new Error("Function not implemented.");
          }}
        ></ChurnersProfileScreen>
      }
    ></Route>
    <Route path="/base-customer" element={<BaseCustomer results={results} />} />
    <Route path="/call-list" element={<CallListScreen results={results} />} />
  </Routes>
);

const App = () => {
  const [results, setResults] = useState<{ name: string }[]>(() => {
    const storedResults = localStorage.getItem("results");
    return storedResults ? JSON.parse(storedResults) : [];
  });

  const handleProcessComplete = (resultName: string) => {
    if (!results.find((r) => r.name === resultName)) {
      const updated = [...results, { name: resultName }];
      setResults(updated);
      localStorage.setItem("results", JSON.stringify(updated));
    }
  };
  return (
    <Router>
      <div style={{ display: "flex", height: "100vh", width: "100vw" }}>
        <AppRoutes
          handleProcessComplete={handleProcessComplete}
          results={results}
        />
      </div>
    </Router>
  );
};

export default App;
