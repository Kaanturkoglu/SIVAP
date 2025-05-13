import { useEffect, useState } from "react";
import {
  Box,
  Button,
  Typography,
  LinearProgress,
  TextField,
} from "@mui/material";
import FileUploadIcon from "@mui/icons-material/FileUpload";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import Sider from "../../components/Sider";
import { LocalizationProvider, DatePicker } from "@mui/x-date-pickers";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";

interface HomeScreenProps {
  results: { name: string }[];
  onProcessComplete: (resultName: string) => void;
}

const HomeScreen = ({ results, onProcessComplete }: HomeScreenProps) => {
  const navigate = useNavigate();
  const [selectedFolderFiles, setSelectedFolderFiles] = useState<File[]>([]);
  const [selectedExcelFile, setSelectedExcelFile] = useState<File | null>(null);
  const [downloadLink, setDownloadLink] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedDate, setSelectedDate] = useState<string>("");

  useEffect(() => {
    if (downloadLink) {
      const link = document.createElement("a");
      link.href = downloadLink;
      link.download = "processed_files.zip";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadLink);
      setDownloadLink(null);
    }
  }, [downloadLink]);

  const handleDatePreferenceClick = async () => {
    if (!selectedDate || selectedDate.trim() === "") {
      alert("Please enter a date.");
      return;
    }

    const dateFormatRegex = /^\d{4}-\d{2}-\d{2}$/;

    if (!dateFormatRegex.test(selectedDate)) {
      alert("Invalid format. Please enter the date in yyyy-mm-dd format.");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post("http://localhost:8000/set-date", {
        date: selectedDate,
      });
      console.log(response.data);
      alert("Date sent successfully!");
    } catch (error) {
      console.error("Failed to send date:", error);
      alert("Failed to send date.");
    } finally {
      setLoading(false);
    }
  };

  const handleFolderChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files) {
      const files = Array.from(event.target.files);
      if (files.length > 0) {
        setSelectedFolderFiles(files);
        console.log("Selected folder files:", files);
      }
    }
  };

  const handleExcelChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      const file = event.target.files[0];
      setSelectedExcelFile(file);
      console.log("Selected excel file:", file);
    }
  };

  const handleFolderInputClick = () => {
    document.getElementById("folderInput")?.click();
  };

  const handleExcelInputClick = () => {
    document.getElementById("excelInput")?.click();
  };

  const handleFolderUpload = async () => {
    if (selectedFolderFiles.length === 0) {
      alert("Please select folder files to upload");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    selectedFolderFiles.forEach((file) => formData.append("files", file));

    try {
      console.log("Uploading folder files...");
      const response = await axios.post(
        "http://localhost:8000/upload",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          responseType: "blob",
        }
      );
      console.log("Folder upload response:", response);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      setDownloadLink(url);
      onProcessComplete("-- Detailed Customer Data");
      const dateResponse = await axios.post("http://localhost:8000/set-date", {
        date: "2222-02-22",
      });
    } catch (error) {
      console.error("Folder upload failed:", error);
      alert("Folder file upload failed");
    } finally {
      setLoading(false);
    }
  };

  const handleExcelUpload = async () => {
    if (!selectedExcelFile) {
      alert("Please select an Excel file to upload");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append("file", selectedExcelFile);

    try {
      console.log("Uploading excel file...");
      const response = await axios.post(
        "http://localhost:8000/upload_excel",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
          responseType: "blob",
        }
      );
      console.log("Excel upload response:", response);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      setDownloadLink(url);
      onProcessComplete("Detailed Customer Data");
      const dateResponse = await axios.post("http://localhost:8000/set-date", {
        date: "2222-02-22",
      });
    } catch (error) {
      console.error("Excel upload failed:", error);
      alert("Excel file upload failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        flexGrow: 1,
        backgroundColor: "#1e1e2f",
        scrollBehavior: "smooth",
        overflow: "auto",
        height: "100vh",
        display: "flex",
      }}
    >
      <Box sx={{ width: "340px", backgroundColor: "#8b9dc3" }}>
        <Sider
          results={results}
          onResultClick={() => {
            navigate("/data-show");
          }}
        />
      </Box>
      <Box
        sx={{
          flexGrow: 1,
          paddingX: 3,
          backgroundColor: "#1e1e2f",
          display: "flex",
          flexDirection: "column",
          height: "100vh",
          overflow: "auto",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Box
          sx={{
            paddingBottom: "20px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <TextField
            label="Enter Cutoff Date"
            placeholder="yyyy-mm-dd"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            variant="outlined"
            sx={{
              mb: 2,
              width: "300px",
              "& .MuiOutlinedInput-root": {
                backgroundColor: "#1e1e2f",
                color: "white",
                "& fieldset": { borderColor: "#667eea" },
                "&:hover fieldset": { borderColor: "#764ba2" },
                "&.Mui-focused fieldset": { borderColor: "#764ba2" },
              },
              "& .MuiInputLabel-root": { color: "#667eea" },
            }}
          />

          <Button
            variant="contained"
            color="secondary"
            onClick={handleDatePreferenceClick}
            disabled={!selectedDate || loading}
            sx={{
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              color: "white",
              padding: "10px 20px",
              fontSize: "16px",
              marginBottom: "20px",
            }}
          >
            {loading ? "Sending Date..." : "Set Date Preference"}
          </Button>
        </Box>

        <input
          id="folderInput"
          type="file"
          style={{ display: "none" }}
          ref={(input) => {
            if (input) {
              input.setAttribute("webkitdirectory", "");
              input.setAttribute("directory", "");
            }
          }}
          multiple
          onChange={handleFolderChange}
        />
        <input
          id="excelInput"
          type="file"
          style={{ display: "none" }}
          accept=".xls,.xlsx"
          onChange={handleExcelChange}
        />

        {/* Buttons side by side with identical styling */}
        <Box
          sx={{
            display: "flex",
            gap: 2,
            alignItems: "center",
            marginY: "127px",
          }}
        >
          {/* Folder upload & process */}
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <Button
              disableElevation
              disableRipple
              onClick={handleFolderInputClick}
            >
              <Box
                sx={{
                  display: "flex",
                  height: "300px",
                  width: "300px",
                  borderRadius: "15px",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  background:
                    "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                  margin: "5px",
                  boxShadow: "0px 5px 15px rgba(0,0,0,0.3)",
                  transition: "0.3s",
                  "&:hover": { transform: "scale(1.05)" },
                }}
              >
                <Typography
                  sx={{
                    fontFamily: "Arial",
                    fontSize: "20px",
                    fontWeight: "bold",
                    color: "white",
                  }}
                >
                  Upload Raw Data Folder
                </Typography>
                <FileUploadIcon sx={{ fontSize: 50, color: "white" }} />
              </Box>
            </Button>
            <Button
              variant="contained"
              color="primary"
              onClick={handleFolderUpload}
              disabled={selectedFolderFiles.length === 0 || loading}
              sx={{
                background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                color: "white",
                padding: "10px 20px",
                fontSize: "16px",
                marginX: "50px",
              }}
            >
              {loading ? (
                <Typography sx={{ color: "white", fontWeight: "bold" }}>
                  Processing Folder...
                </Typography>
              ) : (
                "Process & Download Folder Files"
              )}
            </Button>
          </Box>

          {/* Excel upload & process */}
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
            }}
          >
            <Button
              disableElevation
              disableRipple
              onClick={handleExcelInputClick}
            >
              <Box
                sx={{
                  display: "flex",
                  height: "300px",
                  width: "300px",
                  borderRadius: "15px",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  background:
                    "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                  margin: "5px",
                  boxShadow: "0px 5px 15px rgba(0,0,0,0.3)",
                  transition: "0.3s",
                  "&:hover": { transform: "scale(1.05)" },
                }}
              >
                <Typography
                  sx={{
                    fontFamily: "Arial",
                    fontSize: "20px",
                    fontWeight: "bold",
                    color: "white",
                  }}
                >
                  Upload Hazır_DB.xlsx
                </Typography>
                <FileUploadIcon sx={{ fontSize: 50, color: "white" }} />
              </Box>
            </Button>
            <Button
              variant="contained"
              color="primary"
              onClick={handleExcelUpload}
              disabled={!selectedExcelFile || loading}
              sx={{
                background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                color: "white",
                padding: "10px 20px",
                fontSize: "16px",
                marginX: "50px",
              }}
            >
              {loading ? (
                <Typography sx={{ color: "white", fontWeight: "bold" }}>
                  Processing Excel...
                </Typography>
              ) : (
                "Process & Download Excel File"
              )}
            </Button>
          </Box>
        </Box>
      </Box>

      {loading && (
        <LinearProgress sx={{ width: "100%", position: "absolute", top: 0 }} />
      )}

      {downloadLink && (
        <Box sx={{ textAlign: "center", marginTop: 2 }}>
          <a
            href={downloadLink}
            download="processed_files.zip"
            style={{ color: "white" }}
          >
            Download Processed Files
          </a>
        </Box>
      )}
    </Box>
  );
};

export default HomeScreen;
