#/////////////////  Use this pattern to gererate a GUI to manipulate a struct.

import progSpec
import codeDogParser
from progSpec import cdlog, cdErr


classString = r"""
struct <VALUE_TYPE>{
    me <KEY_TYPE>: key
    me bool: isBlack
    their <VALUE_TYPE>: left
    their <VALUE_TYPE>: right
    their <VALUE_TYPE>: parent

}

struct RBTree{
    their <VALUE_TYPE>: Root
    their <VALUE_TYPE>: Leaf
    me int: size

    me bool: isLeftChild(their <VALUE_TYPE>: node) <- {
    if(node.parent != NULL and node === node.parent.left){return(true)}
    {return(false)}
    }

    me void: leftRotate(their <VALUE_TYPE>: node, me bool: changeColor) <- {
    their <VALUE_TYPE>: temp <- node.right
    node.right <- temp.left
    node.right.parent <- node
    if(node.parent == NULL){
        Root <- temp
        temp.parent <- NULL
    }else{
        temp.parent <- node.parent
        if(isLeftChild(node)){
        temp.parent.left <- temp
        }else{
        temp.parent.right <- temp
        }
    }
    temp.left <- node
    node.parent <- temp

    if(changeColor == true) {
            node.isBlack <- true
            node.parent.isBlack <- false
        }
    }

    me void: rightRotate(their <VALUE_TYPE>: node, me bool: changeColor) <- {
    their <VALUE_TYPE>: temp <- node.left
    node.left <- temp.right
    node.left.parent <- node
    if(node.parent == NULL){
        Root <- temp
        temp.parent <- NULL
    }else{
        temp.parent <- node.parent
        if(isLeftChild(node) == false){
        temp.parent.right <- temp
        }else{
        temp.parent.left <- temp
        }
    }
    temp.right <- node
    node.parent <- temp

    if(changeColor == true) {
            node.isBlack <- true
            node.parent.isBlack <- false
        }
    }

    me void: rotate(their <VALUE_TYPE>: node)<-{
    if(isLeftChild(node) == true){
        if(isLeftChild(node.parent) == true){
        rightRotate(node.parent.parent, false)
        node.isBlack <-false
        node.parent.isBlack <- true
        node.parent.right.isBlack <- false
        return()
        }
        rightRotate(node.parent, false)
        leftRotate(node.parent.parent, false)
        node.isBlack <-true
        node.right.isBlack <- false
        node.left.isBlack <- false
        return()
    }
    if(isLeftChild(node.parent) == false){
        leftRotate(node.parent.parent, false)
        node.isBlack <-false
        node.parent.isBlack <- true
        node.parent.left.isBlack <- false
        return()
    }
    leftRotate(node.parent, false)
    rightRotate(node.parent.parent, false)
    node.isBlack <-true
    node.right.isBlack <- false
    node.left.isBlack <- false
    return()
    }

    me void: correctTree(their <VALUE_TYPE>: node)<-{
    if(node.parent===Root){
        print ('PARENT ', node.parent.key,' is Root.  Node key is ', node.key, '\n')
        exit(1)
    }
    if(isLeftChild(node.parent) == true){
        if(node.parent.parent.right.isBlack == true){
        rotate(node)
        return()
        }
        node.parent.parent.right.isBlack <- true
        node.parent.parent.isBlack <- false
        node.parent.isBlack <- true
        return()
    }
    if(node.parent.parent.left.isBlack == true){
        rotate(node)
        return()
    }
    node.parent.parent.left.isBlack <- true
    node.parent.parent.isBlack <- false
    node.parent.isBlack <- true
    return()
    }

    me void: checkColor(their <VALUE_TYPE>: node) <-{
    if(node === Root or node === Leaf){
        Root.isBlack <- true
        return()
    }
    if(node.isBlack == false and node.parent.isBlack == false){correctTree(node)}
    checkColor(node.parent)
    }

    me void: BSTInsert(their <VALUE_TYPE>: root, their <VALUE_TYPE>: newNode) <- {
    if (newNode.key > root.key){
        if(root.right === Leaf){
        root.right <- newNode
        newNode.parent <- root
        return()
        }
        BSTInsert(root.right, newNode)
        return()
    }
    if(root.left === Leaf){
        root.left <- newNode
        newNode.parent <-root
        return()
    }
    BSTInsert(root.left, newNode)
    return()
    }

    me void: insert(me int: key) <- {
    their <VALUE_TYPE>: newNode
    if(Root == NULL){
        Allocate(Leaf)
        Leaf.isBlack <-true
        Allocate(newNode)
        newNode.key <- key
        newNode.isBlack <-true
        newNode.left <- Leaf
        newNode.right <- Leaf
        Root <- newNode
        size <- size + 1
        return()
    }
    Allocate(newNode)
    newNode.key <- key
    newNode.left <- Leaf
    newNode.right <- Leaf
    BSTInsert(Root, newNode)
    size <- size + 1
    checkColor(newNode)
    }

    me int: height()<-{
    if(Root == NULL){return (0)}
    return(heightHelper(Root)-1)
    }

    me int: heightHelper(their <VALUE_TYPE>: node)<-{
    if(node == NULL){return (0)}
    me int: leftHeight <- heightHelper(node.left)+1
    me int: rightHeight <- heightHelper(node.right)+1
    if(leftHeight > rightHeight){return (leftHeight)}
    return (rightHeight)

    }

    me void: remove(me int: key) <- {
    print('remove: ', key,'\n')
    their <VALUE_TYPE>: node
    node <- getNode(Root, key)
    removeHelper(node, key)
    }

    me void: removeHelper(their <VALUE_TYPE>: node, their int: key) <- {
        if(node === Leaf or node == NULL) {return()}
        if(node.key == key) {
            if(node.right === Leaf or node.left === Leaf) {deleteOneChild(node)}
        else {
                their <VALUE_TYPE>: inorderSuccessor <- findSmallest(node.right)
                node.key <- inorderSuccessor.key
                removeHelper(node.right, node.key)
            }
        }
        if(node.key < key) {removeHelper(node.right, key)}
    else {removeHelper(node.left, key)}
    }

    me void: deleteOneChild(their <VALUE_TYPE>: nodeToBeDelete) <- {
        their <VALUE_TYPE>: child
    if(nodeToBeDelete.right === Leaf){child <- nodeToBeDelete.left}
    else{child <- nodeToBeDelete.right}
        replaceNode(nodeToBeDelete, child)
        if(nodeToBeDelete.isBlack == true) {
            if(child.isBlack == false) {child.isBlack <- true}
        else {deleteCase1(child)}
        }
    }

    me void: replaceNode(their <VALUE_TYPE>: node, their <VALUE_TYPE>: child) <- {
        child.parent <- node.parent
        if(node.parent == NULL) {Root <-child}
        else {
            if(isLeftChild(node)) {node.parent.left <- child}
        else {node.parent.right <- child}
        }
    }

    their <VALUE_TYPE>: findSmallest(their <VALUE_TYPE>: node) <- {
        their <VALUE_TYPE>: prev <- NULL
/*        withEach count in WHILE(node != NULL and node != Leaf):{
            prev <- node
            node <- node.left
        }
    if(prev != NULL){return (prev)}*/
        return (node)
    }

    me void: deleteCase1(their <VALUE_TYPE>: doubleBlackNode) <- {
    print ('deleteCase1: ', doubleBlackNode.key, '\n')
    if(doubleBlackNode === Leaf){print('    Leaf\n')}
        if(doubleBlackNode.parent == NULL) {
            Root <- doubleBlackNode
            return()
        }
        deleteCase2(doubleBlackNode)
    }

    me void: deleteCase2(their <VALUE_TYPE>: doubleBlackNode) <- {
    print ('deleteCase2: ', doubleBlackNode.key, '\n')
    their <VALUE_TYPE>: siblingNode
    siblingNode <- findSiblingNode(doubleBlackNode)
        if(siblingNode.isBlack == false) {
            if(isLeftChild(siblingNode)) {rightRotate(siblingNode, true)}
        else {leftRotate(siblingNode, true)}
            if(siblingNode.parent == NULL) {Root <- siblingNode}
        }
        deleteCase3(doubleBlackNode)
    }

    me void: deleteCase3(their <VALUE_TYPE>: doubleBlackNode) <- {
    print ('deleteCase3: ', doubleBlackNode.key, '\n')
    their <VALUE_TYPE>: siblingNode <- findSiblingNode(doubleBlackNode)
        if(doubleBlackNode.parent.isBlack == true and siblingNode.isBlack == true and siblingNode.left.isBlack == true and siblingNode.right.isBlack == true) {
            siblingNode.isBlack <- false
            deleteCase1(doubleBlackNode.parent)
        } else {
            deleteCase4(doubleBlackNode)
        }
    }

    me void: deleteCase4(their <VALUE_TYPE>: doubleBlackNode) <- {
        print ('deleteCase4: ', doubleBlackNode.key, '\n')
        their <VALUE_TYPE>: siblingNode <- findSiblingNode(doubleBlackNode)
        if(doubleBlackNode.parent.isBlack == false and siblingNode.isBlack == true and siblingNode.left.isBlack == true and siblingNode.right.isBlack == true) {
            siblingNode.isBlack <- false
            doubleBlackNode.parent.isBlack <- true
            return()
        } else {
            deleteCase5(doubleBlackNode)
        }
    }

    me void: deleteCase5(their <VALUE_TYPE>: doubleBlackNode) <- {
    print ('deleteCase5: ', doubleBlackNode.key, '\n')
        their <VALUE_TYPE>: siblingNode <- findSiblingNode(doubleBlackNode)
        if(siblingNode.isBlack == true) {
            if (isLeftChild(doubleBlackNode) == true and siblingNode.right.isBlack == true and siblingNode.left.isBlack == false) {
                rightRotate(siblingNode.left, true)
            } else if (isLeftChild(doubleBlackNode) == false and siblingNode.left.isBlack == true and siblingNode.right.isBlack == false) {
                leftRotate(siblingNode.right, true)
            }
        }
        deleteCase6(doubleBlackNode)
    }

    me void: deleteCase6(their <VALUE_TYPE>: doubleBlackNode) <- {
    print ('deleteCase6: ', doubleBlackNode.key, '\n')
        their <VALUE_TYPE>: siblingNode <- findSiblingNode(doubleBlackNode)
        siblingNode.isBlack <- siblingNode.parent.isBlack
        siblingNode.parent.isBlack <- true
        if(isLeftChild(doubleBlackNode) == true) {
            siblingNode.right.isBlack <- true
            leftRotate(siblingNode, false)
        } else {
            siblingNode.left.isBlack <- true
            rightRotate(siblingNode, false)
        }
        if(siblingNode.parent == NULL) {
            Root <- siblingNode
        }
    }

    their <VALUE_TYPE>: findSiblingNode(their <VALUE_TYPE>: node) <- {
    their <VALUE_TYPE>: parent<- node.parent
        if(isLeftChild(node) == true) {
            return (parent.right)
        } else {
            return (parent.left)
        }
    }

    their <VALUE_TYPE>: get(me int: searchKey) <- {
    their <VALUE_TYPE>: node
    node <- getNode(Root, searchKey)
    return (node)
    }

    their <VALUE_TYPE>: getNode(their <VALUE_TYPE>: node, me int: searchKey) <- {
    while(node != NULL){
        if (searchKey < node.key) {node <- node.left}
        else if (searchKey > node.key) {node <-node.right}
        else if (searchKey == node.key){return (node)}
    }
    return (NULL)
    }

    me void: traverse() <- {
    print('_____________________________________\n')
    print('height: ', height(), '\n')

    print('T R A V E R S E\n')
    traverseHelper(Root, '')
    print('_____________________________________\n')
    }

    me void: traverseHelper(their <VALUE_TYPE>: node, me string: indent) <- {
    me string: isBlackStr
    if (node === Leaf){return()}
    traverseHelper(node.left, indent+"    ")
    if (node.isBlack == true){isBlackStr<-"B"}
    else{isBlackStr<-"R"}
    print(indent, node.key, ':', isBlackStr, '\n')
    traverseHelper(node.right, indent+'    ')
    }

    me int: blackNodes(their <VALUE_TYPE>: node) <- {
    if (node === Root){return(1)}
    me int: rightBlackNodes <- blackNodes(node.right)
    me int: leftBlackNodes <- blackNodes(node.left)
    if (rightBlackNodes != leftBlackNodes){
        print ('ERROR blackNodes: ', rightBlackNodes, ', ', leftBlackNodes)
    }
    if(node.isBlack){leftBlackNodes <- leftBlackNodes + 1}
    return (leftBlackNodes)
    }

}
"""


def apply(classes, tags, keyType, valueType):
    print "APPLY: in Apply\n"
    CODE = classString
    CODE = CODE.replace("<KEY_TYPE>", keyType)
    CODE = CODE.replace("<VALUE_TYPE>", valueType)
    codeDogParser.AddToObjectFromText(classes[0], classes[1], CODE, "map<keyType,valueType>")
    return
