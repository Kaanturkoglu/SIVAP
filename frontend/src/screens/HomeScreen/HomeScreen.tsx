import { useEffect, useState } from "react";
import { Box, Button, Typography, LinearProgress } from "@mui/material";
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
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);

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
      onProcessComplete("Detailed Customer Data");
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
    } catch (error) {
      console.error("Excel upload failed:", error);
      alert("Excel file upload failed");
    } finally {
      setLoading(false);
    }
  };

  const handleDatePreferenceClick = async () => {
    if (!selectedDate) {
      alert("Please select a date first.");
      return;
    }

    try {
      const response = await axios.post("http://localhost:8000/set-date", {
        date: selectedDate.toISOString(),
      });
      alert("Date sent successfully!");
      console.log(response.data);
    } catch (error) {
      console.error("Failed to send date:", error);
      alert("Failed to send date.");
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
        <Button disableElevation disableRipple onClick={handleFolderInputClick}>
          <Box
            sx={{
              display: "flex",
              height: "300px",
              width: "300px",
              borderRadius: "15px",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              margin: "5px",
              boxShadow: "0px 5px 15px rgba(0,0,0,0.3)",
              transition: "0.3s",
              "&:hover": { transform: "scale(1.05)" },
            }}
          >
            <Typography
              style={{
                fontFamily: "Arial",
                fontSize: "20px",
                fontWeight: "bold",
                color: "white",
              }}
            >
              Upload Raw Data Folder
            </Typography>
            <FileUploadIcon style={{ fontSize: "50px", color: "white" }} />
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
            style={{ paddingBottom: "20px" }}
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
                background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                margin: "20px",
                boxShadow: "0px 5px 15px rgba(0,0,0,0.3)",
                transition: "0.3s",
                "&:hover": { transform: "scale(1.05)" },
              }}
            >
              <Typography
                style={{
                  fontFamily: "Arial",
                  fontSize: "20px",
                  color: "white",
                  fontWeight: "bold",
                }}
              >
                Upload test_db.xlsx
              </Typography>
              <FileUploadIcon style={{ fontSize: "50px", color: "white" }} />
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
