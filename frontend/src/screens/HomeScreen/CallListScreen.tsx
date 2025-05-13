// src/screens/CallListScreen.tsx
import { useEffect, useState } from "react";
import * as XLSX from "xlsx";
import { useNavigate } from "react-router-dom";
import JSZip from "jszip";
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from "@mui/material";
import Sider from "../../components/Sider";

interface CallListRow {
  [key: string]: any;
}

interface CallListScreenProps {
  results: { name: string }[];
}

const CallListScreen = ({ results }: CallListScreenProps) => {
  const [rows, setRows] = useState<CallListRow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const loadExcelFiles = async () => {
      const featureFileName = "customer_probabilities_and_classes.xlsx";
      const maxRetries = 3;
      let retryCount = 0;

      while (retryCount < maxRetries) {
        try {
          const response = await fetch("http://localhost:8000/show-excel", {
            method: "GET",
            headers: {
              "Cache-Control": "no-cache, no-store, must-revalidate",
              Pragma: "no-cache",
              Expires: "0",
            },
          });
          if (!response.ok) {
            throw new Error(
              `ZIP dosyası alınamadı: ${response.status} ${response.statusText}`
            );
          }

          const blob = await response.blob();
          const zip = await JSZip.loadAsync(blob);

          if (!zip.files[featureFileName]) {
            throw new Error(`Beklenen dosya bulunamadı: ${featureFileName}`);
          }

          const featureBuffer = await zip.files[featureFileName].async(
            "arraybuffer"
          );
          const workbook = XLSX.read(featureBuffer, { type: "array" });
          const worksheet = workbook.Sheets[workbook.SheetNames[0]];
          const data = XLSX.utils.sheet_to_json<CallListRow>(worksheet);
          setRows(data);
          break;
        } catch (err) {
          retryCount++;
          if (retryCount >= maxRetries) {
            setError(
              err instanceof Error ? err.message : "Bilinmeyen bir hata oluştu"
            );
          } else {
            await new Promise((r) => setTimeout(r, 1000));
          }
        }
      }

      setLoading(false);
    };

    loadExcelFiles();
  }, []);

  // These keys should match the column headers in your Excel file
  const customerKey = "Müşteri Kodu";
  const contractKey = "Sözleşme No";
  const classKey = "Class_0.5";

  const class1Rows = rows.filter((row) => row[classKey] == 1);
  const class0Rows = rows.filter((row) => row[classKey] == 0);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "row",
        height: "100vh",
        width: "100%",
      }}
    >
      {/* Sidebar */}
      <Box sx={{ width: "340px", backgroundColor: "#8b9dc3" }}>
        <Sider
          results={results}
          onResultClick={() => {
            navigate("/data-show");
          }}
        />
      </Box>

      {/* Main content */}
      <Box
        sx={{
          flexGrow: 1,
          px: 3,
          backgroundColor: "#1e1e2f",
          display: "flex",
          flexDirection: "column",
          height: "100vh",
          overflow: "hidden",
        }}
      >
        <Typography
          sx={{
            color: "#8b9dc3",
            fontSize: 30,
            fontFamily: "Arial",
            fontWeight: "bold",
            pt: 2,
          }}
        >
          Call List
        </Typography>

        {loading && (
          <Box sx={{ display: "flex", justifyContent: "center", my: 4 }}>
            <CircularProgress size={40} thickness={4} />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ my: 2 }}>
            {error}
          </Alert>
        )}

        {!loading && !error && rows.length > 0 && (
          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              gap: 2,
              flexGrow: 1,
              overflow: "auto",
              pt: 2,
            }}
          >
            {/* Class 1 Table */}
            <TableContainer component={Paper} sx={{ flex: 1 }}>
              <Table stickyHeader aria-label="Class 1">
                <TableHead>
                  <TableRow>
                    <TableCell
                      sx={{
                        fontWeight: "bold",
                        backgroundColor: "green",
                        color: "#fff",
                      }}
                    >
                      Müşteri No
                    </TableCell>
                    <TableCell
                      sx={{
                        fontWeight: "bold",
                        backgroundColor: "green",
                        color: "#fff",
                      }}
                    >
                      Sözleşme No
                    </TableCell>
                    <TableCell
                      sx={{
                        fontWeight: "bold",
                        backgroundColor: "green",
                        color: "#fff",
                      }}
                    >
                      Class
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {class1Rows.map((row, idx) => (
                    <TableRow key={idx} hover>
                      <TableCell>{row[customerKey]}</TableCell>
                      <TableCell>{row[contractKey]}</TableCell>
                      <TableCell>{row[classKey]}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {/* Class 0 Table */}
            <TableContainer component={Paper} sx={{ flex: 1 }}>
              <Table stickyHeader aria-label="Class 0">
                <TableHead>
                  <TableRow>
                    <TableCell
                      sx={{
                        fontWeight: "bold",
                        backgroundColor: "red",
                        color: "#fff",
                      }}
                    >
                      Müşteri No
                    </TableCell>
                    <TableCell
                      sx={{
                        fontWeight: "bold",
                        backgroundColor: "red",
                        color: "#fff",
                      }}
                    >
                      Sözleşme No
                    </TableCell>
                    <TableCell
                      sx={{
                        fontWeight: "bold",
                        backgroundColor: "red",
                        color: "#fff",
                      }}
                    >
                      Class
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {class0Rows.map((row, idx) => (
                    <TableRow key={idx} hover>
                      <TableCell>{row[customerKey]}</TableCell>
                      <TableCell>{row[contractKey]}</TableCell>
                      <TableCell>{row[classKey]}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {!loading && !error && rows.length === 0 && (
          <Typography variant="body1" sx={{ mt: 2 }}>
            No data available.
          </Typography>
        )}
      </Box>
    </Box>
  );
};

export default CallListScreen;
