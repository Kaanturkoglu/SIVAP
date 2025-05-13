import React from "react";
import { Box, IconButton, Typography } from "@mui/material";
import DataThresholdingIcon from "@mui/icons-material/DataThresholding";
import { useNavigate } from "react-router-dom";
import logo from "/src/assets/bilkentLogo2.png";
import sportsLogo from "/src/assets/sportsLogo.jpg";
import GroupRemoveIcon from "@mui/icons-material/GroupRemove";
import WhatshotIcon from "@mui/icons-material/Whatshot";
import CallIcon from "@mui/icons-material/Call";
import { Call } from "@mui/icons-material";

interface SiderProps {
  results?: { name: string }[];
  onResultClick: (result: { name: string }) => void;
}

const Sider = ({ results, onResultClick }: SiderProps) => {
  const navigate = useNavigate();
  const handleChurnersProfileClick = () => {
    navigate("/churners-profile");
  };
  const handleBaseCustomerClick = () => {
    navigate("/base-customer");
  };
  const handleCallListClick = () => {
    navigate("/call-list");
  };

  return (
    <Box
      display="flex"
      flexDirection="column"
      height="100vh"
      width="380px"
      bgcolor="#8b9dc3"
      boxShadow={0}
      sx={{
        borderRight: "0.3px solid rgb(46, 46, 69)",
        overflow: "hidden",
      }}
    >
      <IconButton
        edge="start"
        sx={{
          display: "flex",
          justifyContent: "start",
          paddingLeft: "40px",
          color: "#3b5998",
          fontSize: "50px",
          fontFamily: "Arial",
          fontWeight: "bold",
          backgroundColor: "#8b9dc3",
          borderRadius: "0px",
          width: "350px",
          borderBottom: "0.3px solid #1e1e2f",
        }}
        aria-label="menu"
        onClick={() => navigate("/")}
        disableRipple
        disableTouchRipple
        disableFocusRipple
      >
        <img
          src={logo}
          alt="Logo"
          style={{ width: "50px", height: "50px", marginRight: "10px" }}
        />
        <Typography
          sx={{
            fontFamily: "Arial",
            fontWeight: "bold",
            color: "#1e1e2f",
            fontSize: "40px",
          }}
        >
          SIMS
        </Typography>
      </IconButton>
      <IconButton
        sx={{
          paddingLeft: "30px",
          paddingY: "16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "start",
          borderBottom: "0.3px solid #1e1e2f",
          borderRadius: "0px",
          width: "340px",
        }}
        onClick={() => handleCallListClick()}
      >
        <Call style={{ color: "#1e1e2f", fontSize: "30px" }} />
        <Typography
          sx={{
            paddingLeft: "8px",
            fontFamily: "Arial",
            fontWeight: "bold",
            color: "#1e1e2f",
            fontSize: "20px",
          }}
        >
          Call List
        </Typography>
      </IconButton>
      <IconButton
        sx={{
          paddingLeft: "30px",
          paddingY: "16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "start",
          borderBottom: "0.3px solid #1e1e2f",
          borderRadius: "0px",
          width: "340px",
        }}
        onClick={() => handleBaseCustomerClick()}
      >
        <WhatshotIcon style={{ color: "#1e1e2f", fontSize: "30px" }} />
        <Typography
          sx={{
            paddingLeft: "8px",
            fontFamily: "Arial",
            fontWeight: "bold",
            color: "#1e1e2f",
            fontSize: "20px",
          }}
        >
          Base Customer
        </Typography>
      </IconButton>
      <IconButton
        sx={{
          paddingLeft: "30px",
          paddingY: "16px",
          display: "flex",
          alignItems: "center",
          justifyContent: "start",
          borderBottom: "0.3px solid #1e1e2f",
          borderRadius: "0px",
          width: "340px",
        }}
        onClick={() => handleChurnersProfileClick()}
      >
        <GroupRemoveIcon style={{ color: "#1e1e2f", fontSize: "30px" }} />
        <Typography
          sx={{
            paddingLeft: "8px",
            fontFamily: "Arial",
            fontWeight: "bold",
            color: "#1e1e2f",
            fontSize: "20px",
          }}
        >
          Churner Profiles
        </Typography>
      </IconButton>
      <Box
        sx={{
          paddingLeft: "28px",
          paddingY: "16px",
          display: "flex",
          alignItems: "center",
        }}
      >
        <DataThresholdingIcon style={{ color: "#1e1e2f", fontSize: "30px" }} />
        <Typography
          sx={{
            paddingLeft: "8px",
            fontFamily: "Arial",
            fontWeight: "bold",
            color: "#1e1e2f",
            fontSize: "20px",
          }}
        >
          Previous Results
        </Typography>
      </Box>
      <Box>
        {(results ?? []).map((result, index) => (
          <Box
            key={index}
            sx={{
              cursor: "pointer",
              paddingLeft: "26px",
              paddingY: "8px",
            }}
            onClick={() => onResultClick(result)}
          >
            <Typography
              sx={{
                fontFamily: "Arial",
                fontWeight: "bold",
                color: "#1e1e2f",
                fontSize: "16px",
              }}
            >
              {result.name}
            </Typography>
          </Box>
        ))}
      </Box>
      <Box
        sx={{
          position: "absolute",
          bottom: 0,
          backgroundColor: "#8b9dc3",
          width: "340px",
          paddingBottom: "12px",
          textAlign: "center",
          alignItems: "center",
          display: "flex",
          overflow: "hidden",
          paddingLeft: "28px",
        }}
      >
        <img
          src={sportsLogo}
          alt="Logo"
          style={{ width: "40px", height: "40px" }}
        />
        <Typography
          sx={{
            fontFamily: "Arial",
            fontWeight: "bold",
            color: "#1e1e2f",
            fontSize: "22px",
            paddingLeft: "8px",
            textAlign: "center",
            display: "flex",
          }}
        >
          Sports International
        </Typography>
      </Box>
    </Box>
  );
};

export default Sider;
