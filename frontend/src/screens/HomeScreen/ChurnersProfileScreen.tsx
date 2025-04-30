import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import FileUploadIcon from "@mui/icons-material/FileUpload";
import { useNavigate } from "react-router-dom";
import Sider from "../../components/Sider";
import { useState } from "react";
import * as XLSX from "xlsx";

interface RowData {
  [key: string]: any;
}

interface ChurnersProfileScreenProps {
  results: { name: string }[];
}

const ChurnersProfileScreen = ({ results }: ChurnersProfileScreenProps) => {
  const navigate = useNavigate();
  const [rows, setRows] = useState<RowData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isClicked, setIsClicked] = useState(false);

  const handleFetchChurnersClick = async () => {
    setIsClicked(true);
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/churners-excel", {
        method: "GET",
        headers: {
          "Cache-Control": "no-cache, no-store, must-revalidate",
          Pragma: "no-cache",
          Expires: "0",
        },
      });

      if (!response.ok) {
        throw new Error(
          `Excel dosyası alınamadı: ${response.status} ${response.statusText}`
        );
      }

      const blob = await response.blob();
      if (blob.size === 0)
        throw new Error("Boş blob alındı, dosya yüklenemedi");

      const buffer = await blob.arrayBuffer();
      const wb = XLSX.read(buffer, { type: "array" });
      const sheet = wb.Sheets[wb.SheetNames[0]];
      const data: RowData[] = XLSX.utils.sheet_to_json<RowData>(sheet);

      setRows(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Bilinmeyen bir hata oluştu"
      );
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
          overflow: "hidden",
          justifyContent: "center",
        }}
      >
        {!isClicked ? (
          <Button
            disableElevation
            disableRipple
            onClick={handleFetchChurnersClick}
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
                margin: "5px",
                boxShadow: "0px 5px 15px rgba(0,0,0,0.3)",
                transition: "0.3s",
                "&:hover": { transform: "scale(1.05)" },
                overflow: "hidden",
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
                Fetch Churners
              </Typography>
              <FileUploadIcon style={{ fontSize: "50px", color: "white" }} />
            </Box>
          </Button>
        ) : loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", my: 4 }}>
            <CircularProgress size={40} thickness={4} />
          </Box>
        ) : error ? (
          <Alert severity="error" sx={{ my: 2 }}>
            {error}
          </Alert>
        ) : rows.length > 0 ? (
          <>
            <Typography
              sx={{
                color: "#8b9dc3",
                fontSize: 30,
                fontFamily: "Arial",
                fontWeight: "bold",
                pt: 2,
                textAlign: "start",
              }}
            >
              Churners Data
            </Typography>
            <Box sx={{ flexGrow: 1, overflow: "hidden", pb: 3 }}>
              <TableContainer component={Paper} sx={{ maxHeight: "100%" }}>
                <Table
                  stickyHeader
                  sx={{ minWidth: 650 }}
                  aria-label="churners table"
                >
                  <TableHead>
                    <TableRow>
                      {Object.keys(rows[0]).map((key) => (
                        <TableCell
                          key={key}
                          sx={{
                            fontWeight: "bold",
                            backgroundColor: "#8b9dc3",
                          }}
                        >
                          {key}
                        </TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((row, i) => (
                      <TableRow key={i} hover>
                        {Object.values(row).map((val, j) => (
                          <TableCell key={j}>{String(val)}</TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Box>
          </>
        ) : (
          <Typography variant="h6" color="white" sx={{ my: 4 }}>
            Veri bulunamadı.
          </Typography>
        )}
      </Box>
    </Box>
  );
};

export default ChurnersProfileScreen;
