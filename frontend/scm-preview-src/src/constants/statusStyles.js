export const STATUS_STYLES={
 "출고완료":{background:"#d9e8f7",color:"#28547e"},"상담완료":{background:"#d9e8f7",color:"#28547e"},"AS완료":{background:"#d9e8f7",color:"#28547e"},"A/S완료":{background:"#d9e8f7",color:"#28547e"},
 "반품완료":{background:"#f3e7eb",color:"#765b65"},"교환완료":{background:"#e3d9ee",color:"#64507a"},"취소완료":{background:"#e3d9ee",color:"#64507a"},
 "발주요청":{background:"#dceeb9",color:"#42682e"},"교환진행":{background:"#80679f",color:"#fff"},"반품진행":{background:"#f2d6df",color:"#8a5065"},
 "수리중":{background:"#fff4c8",color:"#7b6515"},"발송예약":{background:"#d9e8f7",color:"#28547e"},"상담접수":{background:"#edf2f6",color:"#4b6277"},"회신준비":{background:"#fff4c8",color:"#7b6515"},
 "발주취소":{background:"#f5d8cf",color:"#914c37"},"AS중단":{background:"#f5d8cf",color:"#914c37"},"A/S중단":{background:"#f5d8cf",color:"#914c37"},"수신거부":{background:"#f3d5d1",color:"#934a43"},"오류":{background:"#f3d5d1",color:"#934a43"},"ERROR":{background:"#f3d5d1",color:"#934a43"},
 "사용중지":{background:"#eceeef",color:"#636b73"},"대기":{background:"#fff4c8",color:"#7b6515"},"ON":{background:"#dceeb9",color:"#42682e"},"OFF":{background:"#eceeef",color:"#636b73"},"NORMAL":{background:"#e0e9f5",color:"#465e82"},
 "접속중":{background:"#e6f5e9",color:"#326b40"},"자리비움":{background:"#fff4c8",color:"#7b6515"},"사용중":{background:"#e6f5e9",color:"#326b40"},
 "승인":{background:"#e3f2e5",color:"#316b3e"},"대기":{background:"#fff0d7",color:"#8a5b17"},"재직":{background:"#deebf7",color:"#315f84"},"퇴사":{background:"#eceeef",color:"#666f77"},
};
export const statusStyle=status=>STATUS_STYLES[status]||{background:"#f1f3f4",color:"#525d67"};
