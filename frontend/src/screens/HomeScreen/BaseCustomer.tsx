import { useEffect, useState } from "react";
import * as XLSX from "xlsx";
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
import { useNavigate } from "react-router-dom";

interface RowData {
  [key: string]: any;
}

interface BaseCustomerProps {
  results: { name: string }[];
}

const BaseCustomer = ({ results }: BaseCustomerProps) => {
  const navigate = useNavigate();
  const [rows, setRows] = useState<RowData[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(
          "http://localhost:8000/baseCustomer-excel",
          {
            method: "GET",
            headers: {
              "Cache-Control": "no-cache, no-store, must-revalidate",
              Pragma: "no-cache",
              Expires: "0",
            },
          }
        );

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

    fetchData();
  }, []);

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
          Base Customer Data
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
          <Box sx={{ flexGrow: 1, overflow: "hidden", pb: 3 }}>
            <TableContainer component={Paper} sx={{ maxHeight: "100%" }}>
              <Table
                stickyHeader
                sx={{ minWidth: 650 }}
                aria-label="base table"
              >
                <TableHead>
                  <TableRow>
                    {Object.keys(rows[0]).map((key) => (
                      <TableCell
                        key={key}
                        sx={{ fontWeight: "bold", backgroundColor: "#8b9dc3" }}
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

export default BaseCustomer;
