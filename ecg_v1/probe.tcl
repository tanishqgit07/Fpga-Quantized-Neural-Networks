puts "REPO_PATHS=[get_param board.repoPaths]"
foreach b [get_board_parts] {
    if {[string match -nocase "*arty*" $b] || [string match -nocase "*zybo*" $b] || [string match -nocase "*pynq*" $b] || [string match -nocase "*z7*" $b] || [string match -nocase "*cora*" $b]} {
        puts "BOARD: $b"
    }
}
exit
