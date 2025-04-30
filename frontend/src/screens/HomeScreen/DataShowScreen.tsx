import { useEffect, useState } from "react";
import * as XLSX from "xlsx";
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

interface FeatureRow {
  Feature: string;
  // Diğer kolonlar varsa ekleyin
  [key: string]: any;
}

interface CoefficientRow {
  Feature: string;
  Coefficient: number;
  [key: string]: any;
}

interface DataShowScreenProps {
  results: { name: string }[];
}

const DataShowScreen = ({ results }: DataShowScreenProps) => {
  const [rows, setRows] = useState<FeatureRow[]>([]);
  const [coeffMapping, setCoeffMapping] = useState<CoefficientRow[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [found, setFound] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCoefficient, setSelectedCoefficient] = useState<
    string | number | null
  >(null);
  const [searchLoading, setSearchLoading] = useState<boolean>(false);

  useEffect(() => {
    const loadExcelFiles = async () => {
      const maxRetries = 3;
      let retryCount = 0;

      while (retryCount < maxRetries) {
        try {
          console.log(
            `Trying to fetch Excel files (attempt ${
              retryCount + 1
            }/${maxRetries})`
          );

          const response = await fetch("http://localhost:8000/show-excel", {
            method: "GET",
            headers: {
              "Cache-Control": "no-cache, no-store, must-revalidate",
              Pragma: "no-cache",
              Expires: "0",
            },
          });

          if (!response.ok)
            throw new Error(
              `ZIP dosyası alınamadı: ${response.status} ${response.statusText}`
            );
          console.log("ZIP dosyası alındı: ", response);

          // Read the blob data completely
          const blob = await response.blob();
          console.log(`Blob received, size: ${blob.size} bytes`);

          if (blob.size === 0) {
            throw new Error("Boş blob alındı, dosya yüklenemedi");
          }

          const zip = await JSZip.loadAsync(blob);
          console.log(
            "ZIP dosyası açıldı, içindeki dosyalar:",
            Object.keys(zip.files)
          );

          const featureFileName = "customer_probabilities_and_classes.xlsx";
          const coeffFileName = "logistic_regression_coefficients.xlsx";

          if (!zip.files[featureFileName] || !zip.files[coeffFileName]) {
            throw new Error(
              `ZIP içinde beklenen dosyalar bulunamadı. Bulunan dosyalar: ${Object.keys(
                zip.files
              ).join(", ")}`
            );
          }

          const featureFileBuffer = await zip.files[featureFileName].async(
            "arraybuffer"
          );
          const coeffFileBuffer = await zip.files[coeffFileName].async(
            "arraybuffer"
          );

          console.log(
            `Excel dosyaları okundu. Feature: ${featureFileBuffer.byteLength} bytes, Coeff: ${coeffFileBuffer.byteLength} bytes`
          );

          const featureWorkbook = XLSX.read(featureFileBuffer, {
            type: "array",
          });
          const featureWorksheet =
            featureWorkbook.Sheets[featureWorkbook.SheetNames[0]];
          const featureData =
            XLSX.utils.sheet_to_json<FeatureRow>(featureWorksheet);
          setRows(featureData as FeatureRow[]);
          console.log(`Feature data işlendi, ${featureData.length} satır`);

          const coeffWorkbook = XLSX.read(coeffFileBuffer, { type: "array" });
          const coeffWorksheet =
            coeffWorkbook.Sheets[coeffWorkbook.SheetNames[0]];
          const coeffData =
            XLSX.utils.sheet_to_json<CoefficientRow>(coeffWorksheet);
          setCoeffMapping(coeffData as CoefficientRow[]);
          console.log(`Coefficient data işlendi, ${coeffData.length} satır`);

          break;
        } catch (err) {
          console.error("Excel yükleme hatası:", err);
          retryCount++;

          if (retryCount >= maxRetries) {
            setError(
              err instanceof Error ? err.message : "Bilinmeyen bir hata oluştu"
            );
            console.error("Maksimum yeniden deneme sayısına ulaşıldı.");
          } else {
            console.log(
              `${retryCount}. deneme başarısız, yeniden deneniyor...`
            );
            await new Promise((resolve) => setTimeout(resolve, 1000));
          }
        }
      }

      setLoading(false);
    };

    loadExcelFiles();
  }, []);

  const handleRowClick = (featureName: string) => {
    setSearchLoading(true);
    console.log("Selected feature:", featureName);
    console.log("Coefficient mapping:", coeffMapping);
    setTimeout(() => {
      const foundItem = coeffMapping.find((item) =>
        item.Feature.endsWith(featureName)
      );
      if (foundItem) {
        setFound(true);
        setSelectedCoefficient(foundItem.Coefficient);
      } else {
        setFound(false);
        setSelectedCoefficient("Coefficient bulunamadı");
      }
      setSearchLoading(false);
    }, 500);
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "row",
        height: "100vh",
        width: "100%",
      }}
    >
      <Box sx={{ width: "340px", backgroundColor: "#8b9dc3" }}>
        <Sider results={results} onResultClick={() => {}} />
      </Box>
      <Box
        sx={{
          flexGrow: 1,
          paddingX: 3,
          backgroundColor: "#1e1e2f",
          display: "flex",
          flexDirection: "column",
          height: "100vh",
          overflow: "hidden",
        }}
      >
        <Typography
          style={{
            color: "#8b9dc3",
            fontSize: "30px",
            fontFamily: "Arial",
            fontWeight: "bold",
            paddingTop: "16px",
          }}
        >
          Excel Data
        </Typography>

        {loading && (
          <Box sx={{ display: "flex", justifyContent: "center", my: 4 }}>
            <CircularProgress size={40} thickness={4} />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!loading && !error && rows && rows.length > 0 && (
          <Box sx={{ flexGrow: 1, overflow: "auto", paddingBottom: 3 }}>
            <TableContainer component={Paper} sx={{ maxHeight: "100%" }}>
              <Table
                stickyHeader
                sx={{ minWidth: 650 }}
                aria-label="excel data table"
              >
                <TableHead>
                  <TableRow>
                    {Object.keys(rows[0]).map((key, index) => (
                      <TableCell
                        key={index}
                        sx={{ fontWeight: "bold", backgroundColor: "#8b9dc3" }}
                      >
                        {key}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((row, rowIndex) => (
                    <TableRow
                      key={rowIndex}
                      hover
                      style={{ cursor: "pointer" }}
                    >
                      {Object.values(row).map((val, colIndex) => (
                        <TableCell
                          key={colIndex}
                          onClick={() => handleRowClick(val)}
                        >
                          {String(val)}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Box>
        )}

        {!loading && !error && rows && rows.length === 0 && (
          <Typography variant="body1" sx={{ mt: 2 }}>
            No data available.
          </Typography>
        )}

        {selectedCoefficient !== null && (
          <>
            {searchLoading ? (
              <Box sx={{ display: "flex", justifyContent: "center", my: 2 }}>
                <CircularProgress size={40} thickness={4} />
              </Box>
            ) : found ? (
              <Box
                sx={{
                  mt: 2,
                  padding: 2,
                  paddingBottom: 3,
                  backgroundColor: "#fff",
                  borderRadius: 1,
                }}
              >
                <Typography variant="h6">
                  Selected Feature's Coefficient:
                </Typography>
                <Typography variant="body1">
                  {String(Math.exp(selectedCoefficient))}
                </Typography>
              </Box>
            ) : (
              <Typography variant="body1" sx={{ mt: 2 }}>
                {selectedCoefficient}
              </Typography>
            )}
          </>
        )}
      </Box>
    </Box>
  );
};

export default DataShowScreen;
