"""Textos adicionales."""
import base64
import json
import zlib

_D = (
    "c-nPT&2H2%5Pp?WPOVfT6>*?kkT)^ip!_LGSBR=YZsP8`b>gk#RM4si9)J^1z>z25h}3;C#!hG(2@b1dXFOl#`{wi9c~Y&F_XfOR"
    "Nl8Tu?*P1-ZC!-*qEirTI5S+^gp!R-)K3v3jN~@<K3f3E^Ee7f6=kW-^~1T%luC+Pn4y7&18=vID|q+?f6*~{#Wj>Z@ol)^^`Lvz"
    "!*Xa@r+N!?A-HUM#5z6odS2U5NUE%aoEBx4l9-m>*#Vq-=CiTMG)oo*g&<4vm{yq$O(Y<xE6v(1>t_Y;Xs{&q<!+<C+|N>BRL~%Z"
    "cHbSPfJw=bhlG&#QrxmeX*ha)0O#yd&Fbijgha7@TU#0eiE9pfOlx({_Q8x@__b=svWZuILQCxUIno${GDB^nii9JdfywJZaLwR)"
    ";DAE*oB{7(=%9AWju`dkYGhI7SsE>(I0{MV*-W79C=9ddgg1gsuwA2|<**gVw6h>DpEpyU&^XK>q$Qm?sT3BVAdTp_R!*C-0oeQe"
    ">gWI%cBWyA5}ZrEKO;*&-~c0<1`(NS_Y{Y`psUEuCQ&yC)I93Wd&?I;*Q%CxM#1IKoB0ryWMYg4!N13>V;ZJe_>gnma4i)WOTkrJ"
    "`0cR!+50n`B&(v8Wep{<c%x=cBc@e1BNfshCIuNS^Lz#mzn27-=(G%~f+RU9fyBorDS;LJ_}0y&+<kK*;{z+ZLCQJ6DvMXN*nI^A"
    "A^|O8QjUeG8%17Z3$lo5Leq*`gu}5hv34epii9AC_|Z!4)S0_rQrfG!w_&$X<BfzZLuYAjJ;3z7yUk+V{o~Aq(Cu`h<J_%>Vk~pA"
    "_8{?BquKG{3V3%Tn3inX5Unt7Nt`T_sIsvwTf2pl;}Z@+UBIC`Y7oQ5X^MUrM_?4|%_lQoG7i6CPx*H2X}(s#aKPbV>$@L5ECg2Z"
    "PM{4K%-5c8fpACuZ<9@*^MP!XWoJ!<&J0Kyr5Q|1)%WiI0G#}$iU"
)
T = json.loads(zlib.decompress(base64.b85decode(_D)).decode("utf-8"))
